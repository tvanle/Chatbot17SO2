"""
Generate/Chat API routes.
Handles chat generation with RAG, web search, and thinking modes.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.auth_dependencies import get_optional_current_user
from app.application.chat_history_service import ChatHistoryService
from app.application.factory import ProviderFactory
from app.application.services import DocumentService, RAGService
from app.application.summarization_service import SummarizationService
from app.config.settings import settings
from app.core.mongodb_models import (
    ChatMessageCreate,
    ChatMessageRole,
    ChatSessionCreate,
    ChatSessionUpdate,
    UserInDB,
)
from app.core.models import ChatRequest, ChatResponse, Message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generate"])


async def get_rag_service_from_request(
    thinking_mode: str = "balance",
    enable_web_search: bool = False,
) -> RAGService:
    """
    Create RAG service with specified thinking mode and optional web search.
    
    Args:
        thinking_mode: 'fast', 'balance', or 'thinking' (maps to OpenAI models)
        enable_web_search: Whether to enable web search capability
    """
    try:
        # Get providers (only one of each now)
        embedding = ProviderFactory.get_embedding_provider()
        llm = ProviderFactory.get_llm_provider(model=thinking_mode)
        vector = await ProviderFactory.get_vector_store()
        processor = ProviderFactory.get_document_processor()
        doc_service = DocumentService(processor)

        # Get Redis client for caching
        cache_client = (
            await ProviderFactory.get_redis_client() if settings.enable_cache else None
        )
        
        # Get web search service if enabled
        web_search = None
        if enable_web_search:
            try:
                from app.application.web_search_service import WebSearchService
                web_search = WebSearchService()
            except Exception as e:
                logger.warning(f"Failed to initialize web search: {e}")

        return RAGService(embedding, llm, vector, doc_service, cache_client, web_search)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize service: {str(e)}"
        )


@router.post("/chat", response_model=ChatResponse)
async def generate_chat(
    request: ChatRequest,
    current_user: Optional[UserInDB] = Depends(get_optional_current_user),
):
    """
    Generate chat response with RAG support and thinking modes.

    Thinking Modes:
    - fast: Quick responses (gpt-4-1106-preview)
    - balance: Balanced speed & quality (gpt-4-0125-preview) [default]
    - thinking: Deep reasoning (o4-mini)

    Features:
    - RAG-enabled question answering
    - Configurable retrieval settings
    - Source citations
    - Streaming support
    - Auto-save to chat history (if authenticated)
    - Auto-generate session title
    """
    try:
        # Create RAG service with selected thinking mode and web search if needed
        rag_service = await get_rag_service_from_request(
            thinking_mode=request.thinking_mode.value,
            enable_web_search=request.web_search_config.enabled,
        )

        # Get the last user message
        user_query = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )
        if not user_query:
            raise HTTPException(status_code=400, detail="No user message found")

        # System prompt (thinking mode is handled by model selection)
        system_prompt = request.system_prompt or ""
        
        # Load conversation history from database if session exists
        conversation_history = []
        if request.session_id and current_user:
            try:
                mongodb = await ProviderFactory.get_mongodb_client()
                chat_history_service = ChatHistoryService(mongodb)
                
                # Get existing session with messages
                existing_session = await chat_history_service.get_session(
                    session_id=request.session_id,
                    user_id=current_user.id,
                    include_messages=True,
                )
                
                if existing_session and existing_session.messages:
                    # Convert messages to format expected by RAG
                    conversation_history = [
                        {"role": msg.role.value, "content": msg.content}
                        for msg in existing_session.messages
                    ]
                    logger.info(f"Loaded {len(conversation_history)} messages from session {request.session_id}")
            except Exception as e:
                logger.warning(f"Failed to load conversation history: {e}")
                # Continue without history rather than failing

        # Prepare generation kwargs
        gen_kwargs = {
            "temperature": request.generation_config.temperature,
            "max_tokens": request.generation_config.max_tokens,
            "top_p": request.generation_config.top_p,
            "frequency_penalty": request.generation_config.frequency_penalty,
            "presence_penalty": request.generation_config.presence_penalty,
        }
        if request.generation_config.stop_sequences:
            gen_kwargs["stop"] = request.generation_config.stop_sequences

        # Generate response based on configuration
        answer = None
        sources = None
        web_sources = None
        response_metadata = {
            "thinking_mode": request.thinking_mode.value,
            "collection": request.collection,
            "conversation_turns": len(conversation_history),
        }
        
        # Query with web search if enabled
        if request.web_search_config.enabled:
            result = await rag_service.query_with_web_search(
                query=user_query,
                web_search_config=request.web_search_config,
                rag_config=request.rag_config,
                collection=(
                    request.collection if request.collection != "default" else None
                ),
                **gen_kwargs,
            )
            answer = result["answer"]
            sources = result.get("sources", []) if request.rag_config.include_sources else None
            web_sources = result.get("web_sources", [])
            response_metadata.update({
                "rag_enabled": request.rag_config.enabled,
                "web_search_enabled": True,
                **result.get("metadata", {}),
            })
        # Query with RAG if enabled (no web search)
        elif request.rag_config.enabled:
            result = await rag_service.query(
                query=user_query,
                top_k=request.rag_config.top_k,
                collection=(
                    request.collection if request.collection != "default" else None
                ),
                metadata_filter=request.rag_config.metadata_filter,
                similarity_threshold=request.rag_config.similarity_threshold,
                conversation_history=conversation_history,  # Pass conversation context
                **gen_kwargs,
            )
            answer = result["answer"]
            sources = result["sources"] if request.rag_config.include_sources else None
            response_metadata.update({
                "rag_enabled": True,
                "web_search_enabled": False,
            })
        else:
            # Direct generation without RAG or web search
            context = system_prompt if system_prompt else None
            answer = await rag_service.llm_provider.generate(
                prompt=user_query, context=context, **gen_kwargs
            )
            response_metadata.update({
                "rag_enabled": False,
                "web_search_enabled": False,
            })
        
        # Save to chat history if user is authenticated
        saved_session_id = None
        if current_user:
            try:
                # Initialize chat history service
                mongodb = await ProviderFactory.get_mongodb_client()
                chat_history_service = ChatHistoryService(mongodb)
                summarization_service = SummarizationService(rag_service.llm_provider)
                
                # Create or get session
                if request.session_id:
                    # Use existing session
                    session = await chat_history_service.get_session(
                        session_id=request.session_id,
                        user_id=current_user.id,
                    )
                    if not session:
                        # Session not found or unauthorized, create new one
                        session = await chat_history_service.create_session(
                            user_id=current_user.id,
                            session_create=ChatSessionCreate(),
                        )
                    saved_session_id = session.id
                else:
                    # Create new session
                    session = await chat_history_service.create_session(
                        user_id=current_user.id,
                        session_create=ChatSessionCreate(),
                    )
                    saved_session_id = session.id
                
                # Save user message
                await chat_history_service.add_message(
                    session_id=saved_session_id,
                    user_id=current_user.id,
                    message_create=ChatMessageCreate(
                        session_id=saved_session_id,
                        role=ChatMessageRole.USER,
                        content=user_query,
                        metadata={
                            "thinking_mode": request.thinking_mode.value,
                        },
                    ),
                )
                
                # Save assistant response
                await chat_history_service.add_message(
                    session_id=saved_session_id,
                    user_id=current_user.id,
                    message_create=ChatMessageCreate(
                        session_id=saved_session_id,
                        role=ChatMessageRole.ASSISTANT,
                        content=answer,
                        metadata={
                            "thinking_mode": request.thinking_mode.value,
                            "rag_enabled": response_metadata.get("rag_enabled", False),
                            "web_search_enabled": response_metadata.get("web_search_enabled", False),
                        },
                    ),
                )
                
                # Auto-generate title if needed
                if request.auto_generate_title:
                    session = await chat_history_service.get_session(
                        session_id=saved_session_id,
                        user_id=current_user.id,
                        include_messages=True,
                    )
                    
                    # Check if we should generate title (after 2+ messages)
                    if await summarization_service.should_generate_title(
                        current_message_count=session.message_count,
                        current_title=session.title,
                    ):
                        try:
                            new_title = await summarization_service.generate_title(
                                session.messages
                            )
                            await chat_history_service.update_session(
                                session_id=saved_session_id,
                                user_id=current_user.id,
                                session_update=ChatSessionUpdate(title=new_title),
                            )
                            logger.info(f"Auto-generated title for session {saved_session_id}: {new_title}")
                        except Exception as e:
                            logger.warning(f"Failed to auto-generate title: {e}")
                
                logger.info(f"Saved conversation to session {saved_session_id}")
                
            except Exception as e:
                logger.error(f"Failed to save chat history: {e}")
                # Don't fail the request if chat history save fails
        
        # Build and return response
        return ChatResponse(
            message=Message(role="assistant", content=answer),
            sources=sources,
            web_sources=web_sources,
            metadata=response_metadata,
            session_id=saved_session_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def generate_stream(
    request: ChatRequest,
    current_user: Optional[UserInDB] = Depends(get_optional_current_user),
):
    """
    Stream chat response with real-time chunks in Server-Sent Events format.
    Supports same thinking modes and conversation context as /generate/chat.
    """
    try:
        if not request.stream:
            request.stream = True

        rag_service = await get_rag_service_from_request(
            thinking_mode=request.thinking_mode.value
        )

        user_query = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )
        if not user_query:
            raise HTTPException(status_code=400, detail="No user message found")
        
        # Load conversation history from database if session exists
        conversation_history = []
        if request.session_id and current_user:
            try:
                mongodb = await ProviderFactory.get_mongodb_client()
                chat_history_service = ChatHistoryService(mongodb)
                
                existing_session = await chat_history_service.get_session(
                    session_id=request.session_id,
                    user_id=current_user.id,
                    include_messages=True,
                )
                
                if existing_session and existing_session.messages:
                    conversation_history = [
                        {"role": msg.role.value, "content": msg.content}
                        for msg in existing_session.messages
                    ]
                    logger.info(f"Streaming with {len(conversation_history)} messages from session {request.session_id}")
            except Exception as e:
                logger.warning(f"Failed to load conversation history for streaming: {e}")

        gen_kwargs = {
            "temperature": request.generation_config.temperature,
            "max_tokens": request.generation_config.max_tokens,
        }

        async def event_stream():
            try:
                if request.rag_config.enabled:
                    async for chunk in rag_service.stream_query(
                        user_query,
                        top_k=request.rag_config.top_k,
                        collection=(
                            request.collection
                            if request.collection != "default"
                            else None
                        ),
                        conversation_history=conversation_history,  # Pass conversation context
                        **gen_kwargs,
                    ):
                        # Server-Sent Events format
                        yield f"data: {json.dumps({'content': chunk})}\n\n"
                else:
                    async for chunk in rag_service.llm_provider.stream_generate(
                        user_query, **gen_kwargs
                    ):
                        yield f"data: {json.dumps({'content': chunk})}\n\n"

                # Send done signal
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


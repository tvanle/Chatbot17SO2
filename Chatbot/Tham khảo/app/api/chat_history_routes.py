"""
Chat History API routes.
RESTful endpoints for managing conversation sessions and messages.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth_dependencies import get_current_user
from app.application.chat_history_service import ChatHistoryService
from app.application.factory import ProviderFactory
from app.application.summarization_service import SummarizationService
from app.core.mongodb_models import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatMessageUpdate,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
    ChatSessionWithMessages,
    SummarizeRequest,
    SummarizeResponse,
    UserInDB,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat-history", tags=["chat-history"])


async def get_chat_history_service() -> ChatHistoryService:
    """Dependency to get chat history service."""
    try:
        mongodb = await ProviderFactory.get_mongodb_client()
        return ChatHistoryService(mongodb)
    except Exception as e:
        logger.error(f"Failed to initialize ChatHistoryService: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize service: {str(e)}"
        )


async def get_summarization_service() -> SummarizationService:
    """Dependency to get summarization service."""
    try:
        llm = ProviderFactory.get_llm_provider(model="balance")
        return SummarizationService(llm)
    except Exception as e:
        logger.error(f"Failed to initialize SummarizationService: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize service: {str(e)}"
        )


# ============================================================================
# SESSION ENDPOINTS
# ============================================================================


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    session_create: ChatSessionCreate,
    current_user: UserInDB = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
):
    """
    Create a new chat session.
    
    - Creates an empty conversation session
    - Returns session ID for subsequent message additions
    """
    try:
        session = await service.create_session(
            user_id=current_user.id,
            session_create=session_create,
        )
        return session
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    is_archived: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    current_user: UserInDB = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
):
    """
    List user's chat sessions with pagination.
    
    - Returns sessions ordered by most recent activity
    - Supports filtering by archived status
    - Supports text search in title/summary
    """
    try:
        result = await service.list_sessions(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            is_archived=is_archived,
            search=search,
        )
        return ChatSessionListResponse(**result)
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessages)
async def get_session(
    session_id: str,
    include_messages: bool = Query(default=True),
    current_user: UserInDB = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
):
    """
    Get a specific chat session by ID.
    
    - Returns session details and optionally all messages
    - Only accessible by session owner
    """
    try:
        session = await service.get_session(
            session_id=session_id,
            user_id=current_user.id,
            include_messages=include_messages,
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: str,
    session_update: ChatSessionUpdate,
    current_user: UserInDB = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
):
    """
    Update a chat session.
    
    - Update title, summary, tags, or metadata
    - Only accessible by session owner
    """
    try:
        updated_session = await service.update_session(
            session_id=session_id,
            user_id=current_user.id,
            session_update=session_update,
        )
        
        if not updated_session:
            raise HTTPException(
                status_code=404,
                detail="Session not found or unauthorized"
            )
        
        return updated_session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
):
    """
    Delete a chat session (soft delete).
    
    - Marks session and all its messages as deleted
    - Only accessible by session owner
    """
    try:
        success = await service.delete_session(
            session_id=session_id,
            user_id=current_user.id,
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Session not found or unauthorized"
            )
        
        return {"message": "Session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/archive")
async def archive_session(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
):
    """Archive a session (hide from main list)."""
    try:
        success = await service.archive_session(session_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Session not found or unauthorized"
            )
        
        return {"message": "Session archived successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to archive session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/restore")
async def restore_session(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
):
    """Restore an archived session."""
    try:
        success = await service.restore_session(session_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Session not found or unauthorized"
            )
        
        return {"message": "Session restored successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MESSAGE ENDPOINTS
# ============================================================================


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def add_message(
    session_id: str,
    message_create: ChatMessageCreate,
    current_user: UserInDB = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
):
    """
    Add a message to a chat session.
    
    - Appends message to session
    - Updates session's last_message_at timestamp
    """
    try:
        # Ensure session_id in message matches route parameter
        message_create.session_id = session_id
        
        message = await service.add_message(
            session_id=session_id,
            user_id=current_user.id,
            message_create=message_create,
        )
        
        if not message:
            raise HTTPException(
                status_code=404,
                detail="Session not found or unauthorized"
            )
        
        return message
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add message to session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages")
async def list_messages(
    session_id: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: UserInDB = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
):
    """
    List messages in a session.
    
    - Returns messages in chronological order
    - Supports pagination for long conversations
    """
    try:
        messages = await service.list_messages(
            session_id=session_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )
        
        return {
            "messages": messages,
            "count": len(messages),
            "session_id": session_id,
        }
    except Exception as e:
        logger.error(f"Failed to list messages for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/messages/{message_id}", response_model=ChatMessageResponse)
async def update_message(
    message_id: str,
    update: ChatMessageUpdate,
    current_user: UserInDB = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
):
    """
    Update a message's content.
    
    - Only accessible by session owner
    - Sets edited_at timestamp
    """
    try:
        updated_message = await service.update_message(
            message_id=message_id,
            user_id=current_user.id,
            content=update.content,
        )
        
        if not updated_message:
            raise HTTPException(
                status_code=404,
                detail="Message not found or unauthorized"
            )
        
        return updated_message
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    current_user: UserInDB = Depends(get_current_user),
    service: ChatHistoryService = Depends(get_chat_history_service),
):
    """
    Delete a message (soft delete).
    
    - Only accessible by session owner
    """
    try:
        success = await service.delete_message(
            message_id=message_id,
            user_id=current_user.id,
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Message not found or unauthorized"
            )
        
        return {"message": "Message deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SUMMARIZATION ENDPOINTS
# ============================================================================


@router.post("/sessions/{session_id}/summarize", response_model=SummarizeResponse)
async def summarize_session(
    session_id: str,
    request: Optional[SummarizeRequest] = None,
    current_user: UserInDB = Depends(get_current_user),
    history_service: ChatHistoryService = Depends(get_chat_history_service),
    summarization_service: SummarizationService = Depends(get_summarization_service),
):
    """
    Generate title and summary for a chat session.
    
    - Uses LLM to analyze conversation context
    - Generates concise title and summary
    - Updates session with generated content
    """
    try:
        # Get session with messages
        session = await history_service.get_session(
            session_id=session_id,
            user_id=current_user.id,
            include_messages=True,
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not session.messages:
            raise HTTPException(
                status_code=400,
                detail="Cannot summarize empty session"
            )
        
        # Generate title and summary
        max_length = request.max_length if request else 200
        
        title = await summarization_service.generate_title(session.messages)
        summary = await summarization_service.generate_summary(
            session.messages,
            max_length=max_length
        )
        
        # Update session
        await history_service.update_session(
            session_id=session_id,
            user_id=current_user.id,
            session_update=ChatSessionUpdate(title=title, summary=summary),
        )
        
        return SummarizeResponse(
            session_id=session_id,
            title=title,
            summary=summary,
            message_count=len(session.messages),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to summarize session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/auto-title")
async def auto_generate_title(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user),
    history_service: ChatHistoryService = Depends(get_chat_history_service),
    summarization_service: SummarizationService = Depends(get_summarization_service),
):
    """
    Auto-generate title only (lighter than full summarization).
    
    - Called automatically after first few messages
    - Updates session title based on conversation context
    """
    try:
        # Get session with messages
        session = await history_service.get_session(
            session_id=session_id,
            user_id=current_user.id,
            include_messages=True,
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not session.messages:
            raise HTTPException(
                status_code=400,
                detail="Cannot generate title for empty session"
            )
        
        # Generate title
        title = await summarization_service.generate_title(session.messages)
        
        # Update session
        await history_service.update_session(
            session_id=session_id,
            user_id=current_user.id,
            session_update=ChatSessionUpdate(title=title),
        )
        
        return {
            "session_id": session_id,
            "title": title,
            "message": "Title generated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to auto-generate title for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


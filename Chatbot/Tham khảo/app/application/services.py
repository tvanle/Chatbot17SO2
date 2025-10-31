"""
Application services implementing business logic.
Follows Single Responsibility Principle with caching and advanced features.
"""

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.core.interfaces import (
    IDocumentProcessor,
    IEmbeddingProvider,
    ILLMProvider,
    IVectorStore,
)
from app.infrastructure.databases.redis_client import RedisClient

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document processing and chunking with multiple strategies."""

    def __init__(
        self,
        processor: IDocumentProcessor,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        self.processor = processor
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        logger.info(
            f"DocumentService initialized (chunk_size={self.chunk_size}, overlap={self.chunk_overlap})"
        )

    async def process_file(self, file_path: str) -> str:
        """
        Process a file and return its text content.

        Args:
            file_path: Path to file

        Returns:
            Extracted text content
        """
        try:
            content = await self.processor.process(file_path)
            logger.debug(f"Processed file: {file_path} ({len(content)} chars)")
            return content
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            raise RuntimeError(f"File processing failed: {str(e)}")

    def chunk_text(
        self,
        text: str,
        strategy: str = "fixed",
        chunk_size: int = None,
        overlap: int = None,
    ) -> List[str]:
        """
        Split text into chunks using specified strategy.

        Args:
            text: Text to chunk
            strategy: Chunking strategy ('fixed', 'semantic', 'sentence')
            chunk_size: Override default chunk size
            overlap: Override default overlap

        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.chunk_overlap

        if strategy == "fixed":
            return self._chunk_fixed(text, chunk_size, overlap)
        elif strategy == "semantic":
            return self._chunk_semantic(text, chunk_size, overlap)
        elif strategy == "sentence":
            return self._chunk_sentences(text, chunk_size)
        else:
            logger.warning(f"Unknown strategy '{strategy}', using 'fixed'")
            return self._chunk_fixed(text, chunk_size, overlap)

    def _chunk_fixed(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Fixed-size chunking with overlap."""
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += chunk_size - overlap

            # Prevent infinite loop
            if overlap >= chunk_size:
                break

        logger.debug(
            f"Fixed chunking: {len(chunks)} chunks (size={chunk_size}, overlap={overlap})"
        )
        return chunks

    def _chunk_semantic(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Semantic chunking by paragraphs.
        Tries to keep semantic units together while respecting chunk_size.
        """
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r"\n\n+", text)

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds chunk_size, start new chunk
            if current_chunk and len(current_chunk) + len(para) > chunk_size:
                chunks.append(current_chunk)
                # Add overlap from end of previous chunk
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + " " + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)

        logger.debug(
            f"Semantic chunking: {len(chunks)} chunks from {len(paragraphs)} paragraphs"
        )
        return chunks

    def _chunk_sentences(self, text: str, chunk_size: int) -> List[str]:
        """
        Sentence-based chunking.
        Groups sentences into chunks of approximately chunk_size.
        """
        # Simple sentence splitting (can be improved with NLTK)
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # If adding sentence exceeds chunk_size, start new chunk
            if current_chunk and len(current_chunk) + len(sentence) > chunk_size:
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)

        logger.debug(
            f"Sentence chunking: {len(chunks)} chunks from {len(sentences)} sentences"
        )
        return chunks

    def create_documents(
        self, chunks: List[str], metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Create document objects from chunks.

        Args:
            chunks: List of text chunks
            metadata: Shared metadata for all chunks

        Returns:
            List of document dicts with content and metadata
        """
        metadata = metadata or {}
        return [
            {"content": chunk, "metadata": {**metadata, "chunk_index": i}}
            for i, chunk in enumerate(chunks)
            if chunk and chunk.strip()
        ]


class RAGService:
    """Main RAG orchestration service with caching, web search, and advanced features."""

    def __init__(
        self,
        embedding_provider: IEmbeddingProvider,
        llm_provider: ILLMProvider,
        vector_store: IVectorStore,
        document_service: DocumentService,
        cache_client: Optional[RedisClient] = None,
        web_search_service: Optional["WebSearchService"] = None,
    ):
        self.embedding_provider = embedding_provider
        self.llm_provider = llm_provider
        self.vector_store = vector_store
        self.document_service = document_service
        self.cache = cache_client
        self.web_search = web_search_service
        logger.info(
            f"RAGService initialized (cache={'enabled' if cache_client else 'disabled'}, "
            f"web_search={'enabled' if web_search_service else 'disabled'})"
        )

    async def ingest_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        collection: str = "default",
        chunk_strategy: str = "fixed",
    ) -> Dict[str, Any]:
        """
        Ingest text content into the RAG system.

        Args:
            text: Text content to ingest
            metadata: Document metadata
            collection: Collection name
            chunk_strategy: Chunking strategy

        Returns:
            Dictionary with ingestion results
        """
        try:
            # Chunk text
            chunks = self.document_service.chunk_text(text, strategy=chunk_strategy)
            documents = self.document_service.create_documents(chunks, metadata)

            # Generate embeddings (with cache check)
            embeddings = await self._get_embeddings_cached(
                [d["content"] for d in documents]
            )

            # Store in vector store
            doc_ids = await self.vector_store.add_documents(
                documents, embeddings, collection=collection, doc_metadata=metadata
            )

            logger.info(f"Ingested {len(chunks)} chunks to collection '{collection}'")
            return {
                "doc_ids": doc_ids,
                "chunk_count": len(chunks),
                "collection": collection,
            }

        except Exception as e:
            logger.error(f"Failed to ingest text: {e}")
            raise RuntimeError(f"Text ingestion failed: {str(e)}")

    async def ingest_file(
        self,
        file_path: str,
        metadata: Dict[str, Any] = None,
        collection: str = "default",
    ) -> Dict[str, Any]:
        """
        Ingest a file into the RAG system.

        Args:
            file_path: Path to file
            metadata: Document metadata
            collection: Collection name

        Returns:
            Dictionary with ingestion results
        """
        try:
            text = await self.document_service.process_file(file_path)
            return await self.ingest_text(text, metadata, collection)
        except Exception as e:
            logger.error(f"Failed to ingest file {file_path}: {e}")
            raise RuntimeError(f"File ingestion failed: {str(e)}")
    
    async def reindex_document(
        self,
        document_id: str,
        file_path: str,
        old_vector_ids: List[str],
        collection: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        chunk_strategy: str = "fixed",
    ) -> Dict[str, Any]:
        """
        Re-index a document with updated embeddings.
        
        Args:
            document_id: Document ID in MongoDB
            file_path: Path to document file
            old_vector_ids: List of old vector IDs to delete
            collection: Collection name
            metadata: Updated metadata
            chunk_size: Override chunk size
            chunk_overlap: Override chunk overlap
            chunk_strategy: Chunking strategy
            
        Returns:
            Dictionary with old/new vector IDs and statistics
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Re-indexing document {document_id} ({len(old_vector_ids)} old vectors)")
            
            # Step 1: Delete old vectors from Qdrant
            if old_vector_ids:
                await self.vector_store.delete(old_vector_ids)
                logger.info(f"Deleted {len(old_vector_ids)} old vectors from Qdrant")
            
            # Step 2: Override chunking settings if provided
            original_chunk_size = self.document_service.chunk_size
            original_chunk_overlap = self.document_service.chunk_overlap
            
            if chunk_size:
                self.document_service.chunk_size = chunk_size
            if chunk_overlap:
                self.document_service.chunk_overlap = chunk_overlap
            
            # Step 3: Re-process document
            text = await self.document_service.process_file(file_path)
            chunks = self.document_service.chunk_text(text, strategy=chunk_strategy)
            documents = self.document_service.create_documents(chunks, metadata)
            
            logger.info(f"Generated {len(chunks)} new chunks (strategy: {chunk_strategy})")
            
            # Step 4: Generate new embeddings
            embeddings = await self._get_embeddings_cached(
                [d["content"] for d in documents]
            )
            
            # Step 5: Store new vectors in Qdrant
            new_vector_ids = await self.vector_store.add_documents(
                documents, embeddings, collection=collection, doc_metadata=metadata
            )
            
            logger.info(f"Created {len(new_vector_ids)} new vectors in Qdrant")
            
            # Restore original chunking settings
            self.document_service.chunk_size = original_chunk_size
            self.document_service.chunk_overlap = original_chunk_overlap
            
            elapsed = time.time() - start_time
            logger.info(f"Re-indexing completed in {elapsed:.2f}s")
            
            return {
                "success": True,
                "document_id": document_id,
                "old_chunk_count": len(old_vector_ids),
                "new_chunk_count": len(new_vector_ids),
                "old_vector_ids": old_vector_ids,
                "new_vector_ids": new_vector_ids,
                "processing_time_seconds": round(elapsed, 2),
                "collection": collection,
            }
            
        except Exception as e:
            logger.error(f"Failed to re-index document {document_id}: {e}")
            # Try to restore on error (best effort)
            self.document_service.chunk_size = original_chunk_size
            self.document_service.chunk_overlap = original_chunk_overlap
            raise RuntimeError(f"Re-indexing failed: {str(e)}")

    async def query_with_web_search(
        self,
        query: str,
        web_search_config: "WebSearchConfig",
        rag_config: Optional["RAGConfig"] = None,
        collection: Optional[str] = None,
        **llm_kwargs,
    ) -> Dict[str, Any]:
        """
        Query with web search integration.
        Combines RAG retrieval with real-time web search results.

        Args:
            query: User query
            web_search_config: Web search configuration
            rag_config: RAG configuration (optional)
            collection: Collection to search in
            **llm_kwargs: Additional LLM generation parameters

        Returns:
            Dictionary with answer, sources, and web sources
        """
        try:
            web_sources = []
            web_context = ""
            
            # Perform web search if enabled
            if web_search_config.enabled and self.web_search:
                search_query = web_search_config.query or query
                logger.info(f"Performing web search for: {search_query}")
                
                search_result = await self.web_search.search(
                    query=search_query,
                    config=web_search_config,
                )
                
                if search_result["success"] and search_result["results"]:
                    web_results = search_result["results"]
                    
                    # Format as context
                    if web_search_config.include_in_context:
                        web_context = self.web_search.format_results_for_context(web_results)
                    
                    # Create source citations
                    web_sources = self.web_search.create_web_sources(web_results)
                    
                    logger.info(f"Web search returned {len(web_results)} results")
            
            # Perform RAG retrieval if enabled
            rag_sources = []
            rag_context = ""
            
            if rag_config and rag_config.enabled:
                # Get query embedding
                query_embedding = await self._get_embedding_cached(query)
                
                # Search vector store
                results = await self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=rag_config.top_k,
                    collection=collection,
                    metadata_filter=rag_config.metadata_filter,
                    similarity_threshold=rag_config.similarity_threshold,
                )
                
                if results:
                    # Build RAG context
                    rag_context = "\n\n# Document Knowledge Base\n\n" + "\n\n".join(
                        [f"[Document Source {i+1}]: {doc['content']}" for i, doc in enumerate(results)]
                    )
                    rag_sources = results
                    logger.info(f"RAG retrieved {len(results)} documents")
            
            # Combine contexts
            combined_context = ""
            if web_context and rag_context:
                combined_context = f"{web_context}\n\n{rag_context}"
            elif web_context:
                combined_context = web_context
            elif rag_context:
                combined_context = rag_context
            
            # Generate answer with combined context
            if not combined_context:
                combined_context = "No relevant information found."
            
            answer = await self.llm_provider.generate(
                prompt=query, 
                context=combined_context, 
                **llm_kwargs
            )
            
            return {
                "answer": answer,
                "sources": rag_sources,
                "web_sources": web_sources,
                "metadata": {
                    "web_search_enabled": web_search_config.enabled,
                    "rag_enabled": rag_config.enabled if rag_config else False,
                    "web_source_count": len(web_sources),
                    "rag_source_count": len(rag_sources),
                    "collection": collection,
                },
            }
            
        except Exception as e:
            logger.error(f"Query with web search failed: {e}")
            raise RuntimeError(f"Query failed: {str(e)}")

    async def query(
        self,
        query: str,
        top_k: int = 5,
        collection: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.0,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **llm_kwargs,
    ) -> Dict[str, Any]:
        """
        Query the RAG system with caching and conversation context support.

        Args:
            query: User query
            top_k: Number of context chunks to retrieve
            collection: Collection to search in
            metadata_filter: Filter by metadata
            similarity_threshold: Minimum similarity score
            conversation_history: Previous messages for context [{"role": "user/assistant", "content": "..."}]
            **llm_kwargs: Additional LLM generation parameters

        Returns:
            Dictionary with answer and sources
        """
        try:
            # Check cache for this query (skip if conversation history is provided)
            cache_key = None
            if self.cache and settings.enable_cache and not conversation_history:
                cache_key = self._hash_query(query, top_k, collection, metadata_filter)
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    logger.info(f"Cache HIT for query: {query[:50]}...")
                    return cached_result
                logger.debug(f"Cache MISS for query: {query[:50]}...")

            # Get query embedding (with cache)
            query_embedding = await self._get_embedding_cached(query)

            # Search vector store
            results = await self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                collection=collection,
                metadata_filter=metadata_filter,
                similarity_threshold=similarity_threshold,
            )

            # Build context from RAG results
            rag_context = "\n\n".join(
                [f"[Source {i+1}]: {doc['content']}" for i, doc in enumerate(results)]
            )
            
            # Build conversation context if provided
            conversation_context = ""
            if conversation_history:
                conversation_context = self._build_conversation_context(conversation_history)
                logger.debug(f"Using conversation history: {len(conversation_history)} messages")

            # Combine contexts
            full_context = self._combine_contexts(rag_context, conversation_context)

            # Generate answer with LLM
            answer = await self.llm_provider.generate(
                prompt=query, context=full_context, **llm_kwargs
            )

            result = {
                "answer": answer,
                "sources": results,
                "metadata": {
                    "top_k": top_k,
                    "source_count": len(results),
                    "collection": collection,
                    "has_conversation_context": bool(conversation_history),
                    "conversation_turns": len(conversation_history) if conversation_history else 0,
                },
            }

            # Cache result (only if no conversation history)
            if cache_key and self.cache and not conversation_history:
                await self.cache.set(cache_key, result, ttl=settings.cache_ttl)

            return result

        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise RuntimeError(f"Query failed: {str(e)}")

    async def stream_query(
        self,
        query: str,
        top_k: int = 5,
        collection: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **llm_kwargs
    ):
        """
        Stream query response from RAG system with conversation context.

        Args:
            query: User query
            top_k: Number of context chunks
            collection: Collection to search in
            conversation_history: Previous messages for context
            **llm_kwargs: LLM generation parameters

        Yields:
            Text chunks as they arrive
        """
        try:
            # Get query embedding
            query_embedding = await self._get_embedding_cached(query)

            # Search vector store
            results = await self.vector_store.search(
                query_embedding=query_embedding, top_k=top_k, collection=collection
            )

            # Build RAG context
            rag_context = "\n\n".join([doc["content"] for doc in results])
            
            # Build conversation context if provided
            conversation_context = ""
            if conversation_history:
                conversation_context = self._build_conversation_context(conversation_history)
                logger.debug(f"Streaming with conversation history: {len(conversation_history)} messages")
            
            # Combine contexts
            full_context = self._combine_contexts(rag_context, conversation_context)

            # Stream from LLM
            async for chunk in self.llm_provider.stream_generate(
                prompt=query, context=full_context, **llm_kwargs
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Stream query failed: {e}")
            yield f"[ERROR: {str(e)}]"

    # Cache helpers

    async def _get_embedding_cached(self, text: str) -> List[float]:
        """Get embedding for text with Redis cache."""
        if not self.cache or not settings.enable_cache:
            return await self.embedding_provider.embed_text(text)

        # Check cache
        cached = await self.cache.get_cached_embedding(text, "huggingface", "vietnamese-document-embedding")
        if cached:
            logger.debug(f"Embedding cache HIT")
            return cached

        # Generate and cache
        embedding = await self.embedding_provider.embed_text(text)
        await self.cache.cache_embedding(
            text, embedding, "huggingface", "vietnamese-document-embedding", ttl=7 * 24 * 3600
        )  # 7 days
        return embedding

    async def _get_embeddings_cached(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for batch with caching."""
        if not self.cache or not settings.enable_cache:
            return await self.embedding_provider.embed_batch(texts)

        # Check cache for each text
        embeddings = []
        uncached_indices = []
        uncached_texts = []

        for i, text in enumerate(texts):
            cached = await self.cache.get_cached_embedding(text, "huggingface", "vietnamese-document-embedding")
            if cached:
                embeddings.append(cached)
            else:
                embeddings.append(None)
                uncached_indices.append(i)
                uncached_texts.append(text)

        # Generate uncached embeddings
        if uncached_texts:
            logger.debug(
                f"Cache MISS for {len(uncached_texts)}/{len(texts)} embeddings"
            )
            new_embeddings = await self.embedding_provider.embed_batch(uncached_texts)

            # Insert into result and cache
            for idx, embedding in zip(uncached_indices, new_embeddings):
                embeddings[idx] = embedding
                await self.cache.cache_embedding(texts[idx], embedding, "huggingface", "vietnamese-document-embedding", ttl=7 * 24 * 3600)
        else:
            logger.debug(f"Embedding cache HIT for all {len(texts)} texts")

        return embeddings

    def _hash_embedding(self, text: str) -> str:
        """Generate hash key for embedding cache."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _hash_query(
        self,
        query: str,
        top_k: int,
        collection: Optional[str],
        metadata_filter: Optional[Dict[str, Any]],
    ) -> str:
        """Generate hash key for query cache."""
        key_parts = [query, str(top_k), collection or "", str(metadata_filter or {})]
        key_string = "|".join(key_parts)
        return f"query:{hashlib.sha256(key_string.encode()).hexdigest()[:16]}"
    
    def _build_conversation_context(
        self,
        conversation_history: List[Dict[str, str]],
        max_messages: int = 10,
    ) -> str:
        """
        Build conversation context from message history.
        
        Args:
            conversation_history: List of messages with 'role' and 'content'
            max_messages: Maximum number of recent messages to include
            
        Returns:
            Formatted conversation context string
        """
        if not conversation_history:
            return ""
        
        # Take only the last N messages to avoid context overflow
        recent_messages = conversation_history[-max_messages:]
        
        # Format as conversation
        context_lines = ["=== Conversation History ==="]
        for msg in recent_messages:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "").strip()
            if content:
                context_lines.append(f"{role}: {content}")
        
        context_lines.append("=== End of Conversation ===\n")
        
        return "\n".join(context_lines)
    
    def _combine_contexts(
        self,
        rag_context: str,
        conversation_context: str,
    ) -> str:
        """
        Combine RAG context and conversation context intelligently.
        
        Args:
            rag_context: Context from RAG retrieval
            conversation_context: Context from conversation history
            
        Returns:
            Combined context string
        """
        if not conversation_context:
            return rag_context
        
        if not rag_context:
            return conversation_context
        
        # Combine with clear separation
        combined = f"""{conversation_context}

=== Retrieved Information ===
{rag_context}

**Instructions**: Use the conversation history to understand context and references (like "it", "that", "the previous one"). Use the retrieved information to provide accurate, factual answers. If the question refers to something mentioned earlier in the conversation, use that context to interpret the current question."""
        
        return combined

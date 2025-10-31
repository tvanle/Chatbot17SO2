"""
Chat History Service implementing business logic for conversation management.
Follows Single Responsibility Principle with clean separation of concerns.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.mongodb_models import (
    ChatMessageCreate,
    ChatMessageInDB,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionInDB,
    ChatSessionResponse,
    ChatSessionUpdate,
    ChatSessionWithMessages,
)
from app.infrastructure.databases.mongodb_client import MongoDBClient

logger = logging.getLogger(__name__)


class ChatHistoryService:
    """
    Service for managing chat sessions and messages.
    Provides high-level operations for conversation history.
    """

    def __init__(self, mongodb_client: MongoDBClient):
        """
        Initialize chat history service.
        
        Args:
            mongodb_client: MongoDB client for data operations
        """
        self.mongodb = mongodb_client
        logger.info("ChatHistoryService initialized")

    # ========================================================================
    # SESSION OPERATIONS
    # ========================================================================

    async def create_session(
        self,
        user_id: str,
        session_create: ChatSessionCreate,
    ) -> ChatSessionResponse:
        """
        Create a new chat session for a user.
        
        Args:
            user_id: User ID
            session_create: Session creation data
            
        Returns:
            Created session response
        """
        try:
            session_data = {
                "user_id": user_id,
                "title": session_create.title or "New Conversation",
                "summary": None,
                "metadata": session_create.metadata,
                "tags": session_create.tags,
                "is_archived": False,
                "message_count": 0,
                "last_message_at": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "is_deleted": False,
            }
            
            session_id = await self.mongodb.create_chat_session(session_data)
            session_data["_id"] = session_id
            
            logger.info(f"Created session {session_id} for user {user_id}")
            
            return self._to_session_response(session_data)
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise RuntimeError(f"Session creation failed: {str(e)}")

    async def get_session(
        self,
        session_id: str,
        user_id: str,
        include_messages: bool = False,
    ) -> Optional[ChatSessionWithMessages]:
        """
        Get a chat session by ID.
        
        Args:
            session_id: Session ID
            user_id: User ID (for authorization)
            include_messages: Whether to include messages
            
        Returns:
            Session with optional messages, or None if not found
        """
        try:
            session = await self.mongodb.get_chat_session(session_id)
            
            if not session:
                return None
            
            # Check authorization
            if session["user_id"] != user_id:
                logger.warning(f"Unauthorized access attempt to session {session_id}")
                return None
            
            # Convert to response
            session_response = self._to_session_response(session)
            
            if include_messages:
                messages = await self.list_messages(session_id, user_id)
                return ChatSessionWithMessages(
                    **session_response.model_dump(),
                    messages=messages
                )
            
            return ChatSessionWithMessages(**session_response.model_dump())
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise RuntimeError(f"Failed to get session: {str(e)}")

    async def list_sessions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        is_archived: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List chat sessions for a user with pagination.
        
        Args:
            user_id: User ID
            skip: Number to skip
            limit: Maximum number to return
            is_archived: Filter by archived status
            search: Text search query
            
        Returns:
            Dictionary with sessions, total, skip, limit
        """
        try:
            sessions = await self.mongodb.list_chat_sessions(
                user_id=user_id,
                skip=skip,
                limit=limit,
                is_archived=is_archived,
                search=search,
            )
            
            total = await self.mongodb.count_chat_sessions(
                user_id=user_id,
                is_archived=is_archived,
            )
            
            session_responses = [
                self._to_session_response(session) for session in sessions
            ]
            
            logger.debug(f"Listed {len(sessions)} sessions for user {user_id}")
            
            return {
                "sessions": session_responses,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            raise RuntimeError(f"Failed to list sessions: {str(e)}")

    async def update_session(
        self,
        session_id: str,
        user_id: str,
        session_update: ChatSessionUpdate,
    ) -> Optional[ChatSessionResponse]:
        """
        Update a chat session.
        
        Args:
            session_id: Session ID
            user_id: User ID (for authorization)
            session_update: Update data
            
        Returns:
            Updated session or None if not found/unauthorized
        """
        try:
            # Check authorization
            session = await self.mongodb.get_chat_session(session_id)
            if not session or session["user_id"] != user_id:
                return None
            
            # Prepare update data
            update_data = {}
            if session_update.title is not None:
                update_data["title"] = session_update.title
            if session_update.summary is not None:
                update_data["summary"] = session_update.summary
            if session_update.metadata is not None:
                update_data["metadata"] = session_update.metadata
            if session_update.tags is not None:
                update_data["tags"] = session_update.tags
            if session_update.is_archived is not None:
                update_data["is_archived"] = session_update.is_archived
            
            if not update_data:
                # Nothing to update
                return self._to_session_response(session)
            
            # Update
            success = await self.mongodb.update_chat_session(session_id, update_data)
            
            if not success:
                return None
            
            # Get updated session
            updated_session = await self.mongodb.get_chat_session(session_id)
            
            logger.info(f"Updated session {session_id}")
            
            return self._to_session_response(updated_session)
            
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            raise RuntimeError(f"Failed to update session: {str(e)}")

    async def delete_session(
        self,
        session_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a chat session (soft delete).
        
        Args:
            session_id: Session ID
            user_id: User ID (for authorization)
            
        Returns:
            True if deleted successfully
        """
        try:
            # Check authorization
            session = await self.mongodb.get_chat_session(session_id)
            if not session or session["user_id"] != user_id:
                return False
            
            # Delete session and its messages
            session_deleted = await self.mongodb.delete_chat_session(session_id)
            await self.mongodb.delete_session_messages(session_id)
            
            logger.info(f"Deleted session {session_id}")
            
            return session_deleted
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise RuntimeError(f"Failed to delete session: {str(e)}")

    async def archive_session(self, session_id: str, user_id: str) -> bool:
        """Archive a session."""
        session = await self.mongodb.get_chat_session(session_id)
        if not session or session["user_id"] != user_id:
            return False
        return await self.mongodb.archive_chat_session(session_id)

    async def restore_session(self, session_id: str, user_id: str) -> bool:
        """Restore an archived session."""
        session = await self.mongodb.get_chat_session(session_id)
        if not session or session["user_id"] != user_id:
            return False
        return await self.mongodb.restore_chat_session(session_id)

    # ========================================================================
    # MESSAGE OPERATIONS
    # ========================================================================

    async def add_message(
        self,
        session_id: str,
        user_id: str,
        message_create: ChatMessageCreate,
    ) -> Optional[ChatMessageResponse]:
        """
        Add a message to a chat session.
        
        Args:
            session_id: Session ID
            user_id: User ID (for authorization)
            message_create: Message data
            
        Returns:
            Created message or None if unauthorized
        """
        try:
            # Check authorization
            session = await self.mongodb.get_chat_session(session_id)
            if not session or session["user_id"] != user_id:
                logger.warning(f"Unauthorized message add attempt to session {session_id}")
                return None
            
            # Create message
            message_data = {
                "session_id": session_id,
                "role": message_create.role,
                "content": message_create.content,
                "metadata": message_create.metadata,
                "created_at": datetime.now(),
                "edited_at": None,
                "is_deleted": False,
            }
            
            message_id = await self.mongodb.create_chat_message(message_data)
            message_data["_id"] = message_id
            
            logger.debug(f"Added message to session {session_id}")
            
            return self._to_message_response(message_data)
            
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise RuntimeError(f"Failed to add message: {str(e)}")

    async def list_messages(
        self,
        session_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ChatMessageResponse]:
        """
        List messages in a session.
        
        Args:
            session_id: Session ID
            user_id: User ID (for authorization)
            skip: Number to skip
            limit: Maximum number to return
            
        Returns:
            List of messages
        """
        try:
            # Check authorization
            session = await self.mongodb.get_chat_session(session_id)
            if not session or session["user_id"] != user_id:
                return []
            
            messages = await self.mongodb.list_chat_messages(
                session_id=session_id,
                skip=skip,
                limit=limit,
            )
            
            return [self._to_message_response(msg) for msg in messages]
            
        except Exception as e:
            logger.error(f"Failed to list messages: {e}")
            raise RuntimeError(f"Failed to list messages: {str(e)}")

    async def update_message(
        self,
        message_id: str,
        user_id: str,
        content: str,
    ) -> Optional[ChatMessageResponse]:
        """
        Update a message.
        
        Args:
            message_id: Message ID
            user_id: User ID (for authorization)
            content: New content
            
        Returns:
            Updated message or None if unauthorized
        """
        try:
            # Get message and check authorization
            message = await self.mongodb.get_chat_message(message_id)
            if not message:
                return None
            
            session = await self.mongodb.get_chat_session(message["session_id"])
            if not session or session["user_id"] != user_id:
                return None
            
            # Update
            success = await self.mongodb.update_chat_message(
                message_id,
                {"content": content}
            )
            
            if not success:
                return None
            
            # Get updated message
            updated_message = await self.mongodb.get_chat_message(message_id)
            
            logger.debug(f"Updated message {message_id}")
            
            return self._to_message_response(updated_message)
            
        except Exception as e:
            logger.error(f"Failed to update message {message_id}: {e}")
            raise RuntimeError(f"Failed to update message: {str(e)}")

    async def delete_message(self, message_id: str, user_id: str) -> bool:
        """
        Delete a message.
        
        Args:
            message_id: Message ID
            user_id: User ID (for authorization)
            
        Returns:
            True if deleted successfully
        """
        try:
            # Get message and check authorization
            message = await self.mongodb.get_chat_message(message_id)
            if not message:
                return False
            
            session = await self.mongodb.get_chat_session(message["session_id"])
            if not session or session["user_id"] != user_id:
                return False
            
            # Delete
            success = await self.mongodb.delete_chat_message(message_id)
            
            logger.debug(f"Deleted message {message_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete message {message_id}: {e}")
            raise RuntimeError(f"Failed to delete message: {str(e)}")

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _to_session_response(self, session_data: Dict[str, Any]) -> ChatSessionResponse:
        """Convert session dict to response model."""
        return ChatSessionResponse(
            id=session_data["_id"],
            title=session_data["title"],
            summary=session_data.get("summary"),
            message_count=session_data.get("message_count", 0),
            last_message_at=session_data.get("last_message_at"),
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"],
            metadata=session_data.get("metadata", {}),
            tags=session_data.get("tags", []),
            is_archived=session_data.get("is_archived", False),
        )

    def _to_message_response(self, message_data: Dict[str, Any]) -> ChatMessageResponse:
        """Convert message dict to response model."""
        return ChatMessageResponse(
            id=message_data["_id"],
            session_id=message_data["session_id"],
            role=message_data["role"],
            content=message_data["content"],
            metadata=message_data.get("metadata", {}),
            created_at=message_data["created_at"],
            edited_at=message_data.get("edited_at"),
        )


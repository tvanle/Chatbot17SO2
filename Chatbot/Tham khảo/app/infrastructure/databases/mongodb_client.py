"""
MongoDB client for async operations.
Handles connection pooling and database operations for document and user management.
"""

import logging
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, DuplicateKeyError

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    Async MongoDB client using Motor.
    Manages connection to MongoDB for document metadata and user management.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 27017,
        user: str = "admin",
        password: str = "admin_password",
        database: str = "ami_db",
        connection_url: Optional[str] = None,
    ):
        """
        Initialize MongoDB client.

        Args:
            host: MongoDB host
            port: MongoDB port
            user: MongoDB username
            password: MongoDB password
            database: Database name
            connection_url: Full MongoDB connection URL (if provided, overrides host/port/user/password)
        """
        self.connection_url = connection_url
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database_name = database
        
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        
        if connection_url:
            logger.info(f"Initialized MongoDBClient with connection URL (db={database})")
        else:
            logger.info(f"Initialized MongoDBClient (host={host}, port={port}, db={database})")

    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            # Use provided connection_url or build from components
            if self.connection_url:
                connection_url = self.connection_url
            else:
                connection_url = f"mongodb://{self.user}:{self.password}@{self.host}:{self.port}"
            
            # Create Motor client
            self.client = AsyncIOMotorClient(
                connection_url,
                serverSelectionTimeoutMS=5000,
            )
            
            # Get database
            self.db = self.client[self.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Create indexes
            await self._create_indexes()
            
            logger.info(f"✓ Connected to MongoDB: {self.database_name}")
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise RuntimeError(f"MongoDB connection failed: {str(e)}")

    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("✓ MongoDB connection closed")

    async def _create_indexes(self) -> None:
        """Create necessary indexes for collections."""
        try:
            # Users collection indexes
            await self.db.users.create_index("username", unique=True)
            await self.db.users.create_index("email", unique=True)
            
            # Documents collection indexes
            await self.db.documents.create_index("file_name")
            await self.db.documents.create_index("is_active")
            await self.db.documents.create_index("created_at")
            await self.db.documents.create_index([("title", "text")])
            
            # Vector mappings collection indexes
            await self.db.vector_mappings.create_index("document_id")
            await self.db.vector_mappings.create_index("qdrant_point_id", unique=True)
            
            # Chat sessions collection indexes
            await self.db.chat_sessions.create_index("user_id")
            await self.db.chat_sessions.create_index("created_at")
            await self.db.chat_sessions.create_index("updated_at")
            await self.db.chat_sessions.create_index("is_deleted")
            await self.db.chat_sessions.create_index([("title", "text")])
            
            # Chat messages collection indexes
            await self.db.chat_messages.create_index("session_id")
            await self.db.chat_messages.create_index("created_at")
            await self.db.chat_messages.create_index("is_deleted")
            await self.db.chat_messages.create_index([
                ("session_id", 1),
                ("created_at", 1)
            ])
            
            logger.info("✓ MongoDB indexes created")
            
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

    # User Management
    
    async def create_user(self, user_data: Dict[str, Any]) -> str:
        """
        Create a new user.
        
        Args:
            user_data: User information (username, email, hashed_password, role, etc.)
            
        Returns:
            User ID (string)
            
        Raises:
            DuplicateKeyError: If username or email already exists
        """
        try:
            result = await self.db.users.insert_one(user_data)
            logger.info(f"Created user: {user_data.get('username')}")
            return str(result.inserted_id)
        except DuplicateKeyError as e:
            logger.error(f"Duplicate user: {e}")
            raise ValueError("Username or email already exists")

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        user = await self.db.users.find_one({"username": username})
        if user:
            user["_id"] = str(user["_id"])
        return user

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        user = await self.db.users.find_one({"email": email})
        if user:
            user["_id"] = str(user["_id"])
        return user

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        from bson import ObjectId
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
        return user

    async def list_users(
        self, skip: int = 0, limit: int = 50, is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        List users with pagination.
        
        Args:
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            is_active: Filter by active status (None = all)
            
        Returns:
            List of user dictionaries
        """
        query = {}
        if is_active is not None:
            query["is_active"] = is_active
        
        cursor = self.db.users.find(query).skip(skip).limit(limit)
        users = await cursor.to_list(length=limit)
        
        for user in users:
            user["_id"] = str(user["_id"])
            # Remove sensitive data
            user.pop("hashed_password", None)
        
        return users

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update user information.
        
        Args:
            user_id: User ID
            update_data: Fields to update
            
        Returns:
            True if updated successfully
        """
        from bson import ObjectId
        result = await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete_user(self, user_id: str) -> bool:
        """
        Soft delete user (set is_active=False).
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted successfully
        """
        return await self.update_user(user_id, {"is_active": False})

    # Document Metadata Management
    
    async def create_document(self, doc_data: Dict[str, Any]) -> str:
        """
        Create document metadata.
        
        Args:
            doc_data: Document information (title, file_name, metadata, etc.)
            
        Returns:
            Document ID (string)
        """
        result = await self.db.documents.insert_one(doc_data)
        logger.info(f"Created document: {doc_data.get('title')}")
        return str(result.inserted_id)

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        from bson import ObjectId
        doc = await self.db.documents.find_one({"_id": ObjectId(doc_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def list_documents(
        self,
        skip: int = 0,
        limit: int = 50,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List documents with pagination and filters.
        
        Args:
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            is_active: Filter by active status (None = all)
            search: Text search query
            
        Returns:
            List of document dictionaries
        """
        query = {}
        if is_active is not None:
            query["is_active"] = is_active
        if search:
            query["$text"] = {"$search": search}
        
        cursor = self.db.documents.find(query).skip(skip).limit(limit).sort("created_at", -1)
        docs = await cursor.to_list(length=limit)
        
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        
        return docs

    async def count_documents(self, is_active: Optional[bool] = None) -> int:
        """Count documents."""
        query = {}
        if is_active is not None:
            query["is_active"] = is_active
        return await self.db.documents.count_documents(query)

    async def update_document(self, doc_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update document metadata.
        
        Args:
            doc_id: Document ID
            update_data: Fields to update
            
        Returns:
            True if updated successfully
        """
        from bson import ObjectId
        result = await self.db.documents.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def soft_delete_document(self, doc_id: str) -> bool:
        """
        Soft delete document (set is_active=False).
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if deleted successfully
        """
        return await self.update_document(doc_id, {"is_active": False})

    async def restore_document(self, doc_id: str) -> bool:
        """
        Restore soft-deleted document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if restored successfully
        """
        return await self.update_document(doc_id, {"is_active": True})

    # Vector Mapping Management
    
    async def create_vector_mapping(
        self,
        document_id: str,
        qdrant_point_id: str,
        chunk_index: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create mapping between MongoDB document and Qdrant point.
        
        Args:
            document_id: MongoDB document ID
            qdrant_point_id: Qdrant point UUID
            chunk_index: Index of chunk
            metadata: Additional metadata
            
        Returns:
            Mapping ID (string)
        """
        mapping = {
            "document_id": document_id,
            "qdrant_point_id": qdrant_point_id,
            "chunk_index": chunk_index,
            "metadata": metadata or {},
        }
        result = await self.db.vector_mappings.insert_one(mapping)
        return str(result.inserted_id)

    async def get_mappings_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all vector mappings for a document."""
        cursor = self.db.vector_mappings.find({"document_id": document_id})
        mappings = await cursor.to_list(length=1000)
        
        for mapping in mappings:
            mapping["_id"] = str(mapping["_id"])
        
        return mappings

    async def delete_mappings_by_document(self, document_id: str) -> int:
        """Delete all vector mappings for a document."""
        result = await self.db.vector_mappings.delete_many({"document_id": document_id})
        return result.deleted_count

    async def health_check(self) -> bool:
        """Check MongoDB health."""
        try:
            await self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    # ============================================================================
    # CHAT HISTORY MANAGEMENT
    # ============================================================================
    
    # Chat Session Operations
    
    async def create_chat_session(self, session_data: Dict[str, Any]) -> str:
        """
        Create a new chat session.
        
        Args:
            session_data: Session information (user_id, title, metadata, etc.)
            
        Returns:
            Session ID (string)
        """
        result = await self.db.chat_sessions.insert_one(session_data)
        logger.info(f"Created chat session: {session_data.get('title')} for user {session_data.get('user_id')}")
        return str(result.inserted_id)
    
    async def get_chat_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session by ID."""
        from bson import ObjectId
        session = await self.db.chat_sessions.find_one({
            "_id": ObjectId(session_id),
            "is_deleted": False
        })
        if session:
            session["_id"] = str(session["_id"])
        return session
    
    async def list_chat_sessions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        is_archived: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List chat sessions for a user with pagination and filters.
        
        Args:
            user_id: User ID
            skip: Number of sessions to skip
            limit: Maximum number of sessions to return
            is_archived: Filter by archived status (None = all)
            search: Text search query for title/summary
            
        Returns:
            List of chat session dictionaries
        """
        query = {"user_id": user_id, "is_deleted": False}
        
        if is_archived is not None:
            query["is_archived"] = is_archived
        
        if search:
            query["$text"] = {"$search": search}
        
        cursor = (
            self.db.chat_sessions
            .find(query)
            .skip(skip)
            .limit(limit)
            .sort("updated_at", -1)
        )
        sessions = await cursor.to_list(length=limit)
        
        for session in sessions:
            session["_id"] = str(session["_id"])
        
        return sessions
    
    async def count_chat_sessions(
        self,
        user_id: str,
        is_archived: Optional[bool] = None,
    ) -> int:
        """Count chat sessions for a user."""
        query = {"user_id": user_id, "is_deleted": False}
        if is_archived is not None:
            query["is_archived"] = is_archived
        return await self.db.chat_sessions.count_documents(query)
    
    async def update_chat_session(
        self,
        session_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Update chat session.
        
        Args:
            session_id: Session ID
            update_data: Fields to update
            
        Returns:
            True if updated successfully
        """
        from bson import ObjectId
        from datetime import datetime
        
        update_data["updated_at"] = datetime.now()
        
        result = await self.db.chat_sessions.update_one(
            {"_id": ObjectId(session_id), "is_deleted": False},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def delete_chat_session(self, session_id: str) -> bool:
        """
        Soft delete chat session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if deleted successfully
        """
        return await self.update_chat_session(session_id, {"is_deleted": True})
    
    async def archive_chat_session(self, session_id: str) -> bool:
        """Archive chat session."""
        return await self.update_chat_session(session_id, {"is_archived": True})
    
    async def restore_chat_session(self, session_id: str) -> bool:
        """Restore archived chat session."""
        return await self.update_chat_session(session_id, {"is_archived": False})
    
    async def increment_message_count(self, session_id: str) -> bool:
        """Increment message count for a session."""
        from bson import ObjectId
        from datetime import datetime
        
        result = await self.db.chat_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$inc": {"message_count": 1},
                "$set": {
                    "last_message_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        return result.modified_count > 0
    
    # Chat Message Operations
    
    async def create_chat_message(self, message_data: Dict[str, Any]) -> str:
        """
        Create a new chat message.
        
        Args:
            message_data: Message information (session_id, role, content, etc.)
            
        Returns:
            Message ID (string)
        """
        result = await self.db.chat_messages.insert_one(message_data)
        
        # Increment message count in session
        await self.increment_message_count(message_data["session_id"])
        
        logger.debug(f"Created message in session {message_data['session_id']}")
        return str(result.inserted_id)
    
    async def get_chat_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get chat message by ID."""
        from bson import ObjectId
        message = await self.db.chat_messages.find_one({
            "_id": ObjectId(message_id),
            "is_deleted": False
        })
        if message:
            message["_id"] = str(message["_id"])
        return message
    
    async def list_chat_messages(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List chat messages for a session with pagination.
        
        Args:
            session_id: Session ID
            skip: Number of messages to skip
            limit: Maximum number of messages to return
            
        Returns:
            List of chat message dictionaries
        """
        cursor = (
            self.db.chat_messages
            .find({"session_id": session_id, "is_deleted": False})
            .skip(skip)
            .limit(limit)
            .sort("created_at", 1)  # Oldest first
        )
        messages = await cursor.to_list(length=limit)
        
        for message in messages:
            message["_id"] = str(message["_id"])
        
        return messages
    
    async def count_chat_messages(self, session_id: str) -> int:
        """Count messages in a session."""
        return await self.db.chat_messages.count_documents({
            "session_id": session_id,
            "is_deleted": False
        })
    
    async def update_chat_message(
        self,
        message_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Update chat message.
        
        Args:
            message_id: Message ID
            update_data: Fields to update
            
        Returns:
            True if updated successfully
        """
        from bson import ObjectId
        from datetime import datetime
        
        update_data["edited_at"] = datetime.now()
        
        result = await self.db.chat_messages.update_one(
            {"_id": ObjectId(message_id), "is_deleted": False},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def delete_chat_message(self, message_id: str) -> bool:
        """
        Soft delete chat message.
        
        Args:
            message_id: Message ID
            
        Returns:
            True if deleted successfully
        """
        from bson import ObjectId
        result = await self.db.chat_messages.update_one(
            {"_id": ObjectId(message_id)},
            {"$set": {"is_deleted": True}}
        )
        return result.modified_count > 0
    
    async def delete_session_messages(self, session_id: str) -> int:
        """
        Delete all messages in a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Number of messages deleted
        """
        result = await self.db.chat_messages.update_many(
            {"session_id": session_id},
            {"$set": {"is_deleted": True}}
        )
        return result.modified_count


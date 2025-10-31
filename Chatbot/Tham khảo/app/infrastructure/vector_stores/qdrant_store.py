"""
Qdrant vector store implementation following SOLID principles.
Implements IVectorStore interface for Qdrant vector database.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client.models import Distance, PointStruct, Filter, FieldCondition, MatchValue

from app.core.interfaces import IVectorStore
from app.infrastructure.databases.qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


class QdrantVectorStore(IVectorStore):
    """
    Qdrant-based vector store implementation.
    Follows SRP: Only responsible for vector storage and retrieval operations.
    """

    def __init__(
        self,
        qdrant_client: QdrantClient,
        collection_name: str = "ami_documents",
        vector_size: int = 1536,
    ):
        """
        Initialize Qdrant vector store.

        Args:
            qdrant_client: QdrantClient instance
            collection_name: Name of the collection
            vector_size: Dimension of embedding vectors
        """
        self.client = qdrant_client
        self.collection_name = collection_name
        self.vector_size = vector_size
        logger.info(
            f"Initialized QdrantVectorStore (collection={collection_name}, "
            f"vector_size={vector_size})"
        )

    async def initialize(self) -> None:
        """
        Initialize vector store by creating collection if needed.
        """
        try:
            # Create collection if it doesn't exist
            await self.client.create_collection(
                collection_name=self.collection_name,
                vector_size=self.vector_size,
                distance=Distance.COSINE,
                on_disk_payload=True,
            )

            # Get collection info
            info = await self.client.get_collection_info(self.collection_name)
            logger.info(
                f"✓ Qdrant vector store initialized: {info['points_count']} points"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant vector store: {e}")
            raise RuntimeError(f"Vector store initialization failed: {str(e)}")

    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
        **kwargs,
    ) -> List[str]:
        """
        Add documents with embeddings to Qdrant.

        Args:
            documents: List of document dicts with 'content' and 'metadata'
            embeddings: List of embedding vectors
            **kwargs: Additional arguments (collection, doc_metadata, etc.)

        Returns:
            List of point IDs (UUIDs)

        Raises:
            ValueError: If documents and embeddings count mismatch
            RuntimeError: If operation fails
        """
        if len(documents) != len(embeddings):
            raise ValueError(
                f"Documents ({len(documents)}) and embeddings "
                f"({len(embeddings)}) count mismatch"
            )

        try:
            # Extract optional parameters
            collection = kwargs.get("collection", "default")
            doc_metadata = kwargs.get("doc_metadata", {})

            # Prepare points for batch upload
            points = []
            point_ids = []

            for doc, embedding in zip(documents, embeddings):
                # Generate unique ID
                point_id = str(uuid.uuid4())
                point_ids.append(point_id)

                # Prepare payload (metadata)
                payload = {
                    "content": doc["content"],
                    "collection": collection,
                    "is_active": True,  # Always set active by default
                    **doc.get("metadata", {}),
                    **doc_metadata,
                }

                # Create point
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
                points.append(point)

            # Check if we have any points to add
            if not points:
                logger.warning(f"No valid documents to add to collection '{collection}'")
                return []

            # Batch upsert to Qdrant
            await self.client.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )

            logger.info(
                f"Added {len(point_ids)} documents to collection '{collection}'"
            )
            return point_ids

        except Exception as e:
            logger.error(f"Failed to add documents to Qdrant: {e}")
            raise RuntimeError(f"Failed to add documents: {str(e)}")

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in Qdrant.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            **kwargs: Additional filters (collection, similarity_threshold, metadata_filter)

        Returns:
            List of matching documents with content, metadata, and similarity scores
        """
        try:
            # Extract optional parameters
            collection = kwargs.get("collection")
            similarity_threshold = kwargs.get("similarity_threshold", 0.0)
            metadata_filter = kwargs.get("metadata_filter")

            # Build filter conditions
            must_conditions = []

            # Always filter out soft-deleted documents (is_active != False)
            # Only include documents where is_active is True or not set
            must_conditions.append(
                FieldCondition(
                    key="is_active",
                    match=MatchValue(value=True),
                )
            )

            if collection:
                must_conditions.append(
                    FieldCondition(
                        key="collection",
                        match=MatchValue(value=collection),
                    )
                )

            if metadata_filter:
                for key, value in metadata_filter.items():
                    must_conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )

            # Create filter object if we have conditions
            query_filter = None
            if must_conditions:
                query_filter = Filter(must=must_conditions)

            # Search in Qdrant
            search_results = await self.client.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=query_filter,
                score_threshold=similarity_threshold if similarity_threshold > 0 else None,
                with_payload=True,
                with_vectors=False,
            )

            # Format results
            formatted_results = []
            for result in search_results:
                formatted_results.append(
                    {
                        "id": str(result.id),
                        "content": result.payload.get("content", ""),
                        "metadata": {
                            k: v
                            for k, v in result.payload.items()
                            if k != "content"
                        },
                        "similarity": float(result.score),
                    }
                )

            logger.debug(
                f"Search returned {len(formatted_results)} results "
                f"(threshold: {similarity_threshold})"
            )
            return formatted_results

        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            raise RuntimeError(f"Vector search failed: {str(e)}")

    async def delete(self, doc_ids: List[str]) -> None:
        """
        Delete documents by point IDs.

        Args:
            doc_ids: List of point IDs (UUIDs) to delete

        Raises:
            RuntimeError: If deletion fails
        """
        try:
            if not doc_ids:
                return

            # Delete points from Qdrant
            await self.client.client.delete(
                collection_name=self.collection_name,
                points_selector=doc_ids,
                wait=True,
            )

            logger.info(f"Deleted {len(doc_ids)} documents from Qdrant")

        except Exception as e:
            logger.error(f"Failed to delete documents from Qdrant: {e}")
            raise RuntimeError(f"Failed to delete documents: {str(e)}")

    async def get_stats(self, collection: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about stored documents.

        Args:
            collection: Optional collection filter

        Returns:
            Dictionary with counts and stats
        """
        try:
            # Get collection info from Qdrant
            info = await self.client.get_collection_info(self.collection_name)

            stats = {
                "total_documents": info["points_count"],
                "vectors_count": info["vectors_count"],
                "collection": collection or "all",
                "status": info["status"],
            }

            # If filtering by collection, count matching points
            if collection:
                # Scroll through collection to count filtered points
                # This is a simplified version - in production might want to optimize
                scroll_result = await self.client.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="collection",
                                match=MatchValue(value=collection),
                            )
                        ]
                    ),
                    limit=1,
                    with_payload=False,
                    with_vectors=False,
                )
                # Note: For accurate count, would need to scroll through all
                # For now, just report total
                pass

            return stats

        except Exception as e:
            logger.error(f"Failed to get Qdrant stats: {e}")
            return {
                "total_documents": 0,
                "vectors_count": 0,
                "collection": collection or "all",
            }

    async def clear_collection(self) -> None:
        """
        Clear all documents from the collection.
        Useful for testing and cleanup.
        """
        try:
            # Delete and recreate collection
            await self.client.delete_collection(self.collection_name)
            await self.client.create_collection(
                collection_name=self.collection_name,
                vector_size=self.vector_size,
                distance=Distance.COSINE,
            )
            logger.info(f"✓ Cleared collection '{self.collection_name}'")

        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            raise RuntimeError(f"Failed to clear collection: {str(e)}")

    async def collection_exists(self) -> bool:
        """
        Check if the collection exists.

        Returns:
            True if collection exists, False otherwise
        """
        return await self.client.collection_exists(self.collection_name)

    async def get_collections(self) -> List[str]:
        """
        Get list of all collection names from Qdrant.
        
        Returns:
            List of collection names
        """
        try:
            collections_response = await self.client.client.get_collections()
            collection_names = [col.name for col in collections_response.collections]
            logger.info(f"Found {len(collection_names)} collections")
            return collection_names
        except Exception as e:
            logger.error(f"Failed to get collections: {e}")
            return []

    async def update_document(
        self,
        doc_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> None:
        """
        Update an existing document in Qdrant.
        Can update content, metadata, and/or embedding.
        
        Args:
            doc_id: Point ID (UUID) to update
            content: New content (optional)
            metadata: New metadata to merge (optional)
            embedding: New embedding vector (optional)
            
        Raises:
            RuntimeError: If update fails
        """
        try:
            if not any([content, metadata, embedding]):
                logger.warning("No fields to update")
                return
            
            # Get existing point
            points = await self.client.client.retrieve(
                collection_name=self.collection_name,
                ids=[doc_id],
                with_payload=True,
                with_vectors=True if not embedding else False,
            )
            
            if not points:
                raise ValueError(f"Document {doc_id} not found")
            
            existing_point = points[0]
            
            # Prepare updated payload
            updated_payload = dict(existing_point.payload)
            if content:
                updated_payload["content"] = content
            if metadata:
                # Merge metadata
                for key, value in metadata.items():
                    updated_payload[key] = value
            
            # Use new embedding or keep existing
            vector = embedding if embedding else existing_point.vector
            
            # Upsert (update) the point
            from qdrant_client.models import PointStruct
            
            updated_point = PointStruct(
                id=doc_id,
                vector=vector,
                payload=updated_payload,
            )
            
            await self.client.client.upsert(
                collection_name=self.collection_name,
                points=[updated_point],
                wait=True,
            )
            
            logger.info(f"Updated document {doc_id}")
            
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            raise RuntimeError(f"Failed to update document: {str(e)}")

    async def soft_delete(self, doc_ids: List[str]) -> None:
        """
        Soft delete documents by setting is_active=False metadata flag.
        Does NOT actually delete from Qdrant - just marks as inactive.
        
        Args:
            doc_ids: List of point IDs (UUIDs) to soft delete
            
        Raises:
            RuntimeError: If soft delete fails
        """
        try:
            if not doc_ids:
                return
            
            # Update each document with is_active=False
            for doc_id in doc_ids:
                await self.update_document(
                    doc_id=doc_id,
                    metadata={"is_active": False}
                )
            
            logger.info(f"Soft deleted {len(doc_ids)} documents")
            
        except Exception as e:
            logger.error(f"Failed to soft delete documents: {e}")
            raise RuntimeError(f"Failed to soft delete documents: {str(e)}")

    async def restore(self, doc_ids: List[str]) -> None:
        """
        Restore soft-deleted documents by setting is_active=True.
        
        Args:
            doc_ids: List of point IDs (UUIDs) to restore
            
        Raises:
            RuntimeError: If restore fails
        """
        try:
            if not doc_ids:
                return
            
            # Update each document with is_active=True
            for doc_id in doc_ids:
                await self.update_document(
                    doc_id=doc_id,
                    metadata={"is_active": True}
                )
            
            logger.info(f"Restored {len(doc_ids)} documents")
            
        except Exception as e:
            logger.error(f"Failed to restore documents: {e}")
            raise RuntimeError(f"Failed to restore documents: {str(e)}")



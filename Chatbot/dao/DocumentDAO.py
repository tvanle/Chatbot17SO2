"""
DocumentDAO - Data Access Object for Document entity
"""
from typing import Optional
from sqlalchemy.orm import Session
from Chatbot.models.Document import Document


class DocumentDAO:
    """
    DAO for Document operations
    Handles CRUD operations for documents table
    """

    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, doc_id: str) -> Optional[Document]:
        """
        Find document by ID

        Args:
            doc_id: Document UUID

        Returns:
            Document object or None
        """
        return self.db.query(Document).filter(Document.id == doc_id).first()

    def upsert(self, document: Document) -> str:
        """
        Insert or update document

        Args:
            document: Document object to upsert

        Returns:
            Document ID
        """
        existing = self.find_by_id(document.id) if document.id else None

        if existing:
            # Update existing document
            existing.source_uri = document.source_uri
            existing.title = document.title
            existing.text = document.text
            self.db.commit()
            self.db.refresh(existing)
            return existing.id
        else:
            # Insert new document
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            return document.id

    def create(self, source_uri: str, title: str, text: str) -> Document:
        """
        Create a new document

        Args:
            source_uri: Source URI of document
            title: Document title
            text: Full text content

        Returns:
            Created Document object
        """
        doc = Document(source_uri=source_uri, title=title, text=text)
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def delete(self, doc_id: str) -> bool:
        """
        Delete document by ID (cascades to chunks and embeddings)

        Args:
            doc_id: Document UUID

        Returns:
            True if deleted, False if not found
        """
        doc = self.find_by_id(doc_id)
        if doc:
            self.db.delete(doc)
            self.db.commit()
            return True
        return False

    def find_all(self, limit: int = 100, offset: int = 0):
        """
        Get all documents with pagination

        Args:
            limit: Max results
            offset: Starting position

        Returns:
            List of Document objects
        """
        return self.db.query(Document).limit(limit).offset(offset).all()

"""
MinIO storage provider implementation.
S3-compatible object storage for file uploads.
"""

import logging
import uuid
from datetime import timedelta
from io import BytesIO
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.core.interfaces import IStorageProvider

logger = logging.getLogger(__name__)


class MinIOStorage(IStorageProvider):
    """
    MinIO storage provider for file uploads.
    Implements S3-compatible object storage interface.
    """
    
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str = "ami-uploads",
        secure: bool = False,
    ):
        """
        Initialize MinIO storage.
        
        Args:
            endpoint: MinIO server endpoint (e.g., "localhost:9000")
            access_key: Access key for authentication
            secret_key: Secret key for authentication
            bucket: Default bucket name
            secure: Use HTTPS if True
        """
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self.bucket = bucket
        self.endpoint = endpoint
        self.secure = secure
        self._ensure_bucket_exists()
        logger.info(f"MinIO Storage initialized (endpoint: {endpoint}, bucket: {bucket})")
    
    # ===== PATH BUILDERS =====
    
    @staticmethod
    def build_upload_path(
        user_id: str,
        session_id: Optional[str] = None,
        file_type: str = "files"
    ) -> str:
        """
        Build path for user uploads.
        
        Structure: upload/{user_id}/{session_id}/{file_type}/
        
        Args:
            user_id: User ID
            session_id: Session ID (optional, uses 'general' if not provided)
            file_type: Type subfolder (images, documents, thumbnails)
            
        Returns:
            Path string (e.g., "upload/user123/session456/images/")
        """
        session = session_id if session_id else "general"
        return f"upload/{user_id}/{session}/{file_type}"
    
    @staticmethod
    def build_data_path(data_type: str = "documents") -> str:
        """
        Build path for system data (vector/document storage).
        
        Structure: data/{data_type}/
        
        Args:
            data_type: Data category (documents, embeddings, etc.)
            
        Returns:
            Path string (e.g., "data/documents/")
        """
        return f"data/{data_type}"
    
    @staticmethod
    def build_generated_path(content_type: str = "images") -> str:
        """
        Build path for AI-generated content.
        
        Structure: generated/{content_type}/
        
        Args:
            content_type: Content category (images, text, etc.)
            
        Returns:
            Path string (e.g., "generated/images/")
        """
        return f"generated/{content_type}"
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"✓ Created bucket: {self.bucket}")
            else:
                logger.debug(f"Bucket already exists: {self.bucket}")
        except S3Error as e:
            logger.error(f"Failed to create bucket: {e}")
            raise RuntimeError(f"Bucket creation failed: {str(e)}")
    
    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        path_prefix: Optional[str] = None,
    ) -> str:
        """
        Upload file to MinIO.
        
        Args:
            file_data: File bytes
            filename: Original filename
            content_type: MIME type (e.g., "image/jpeg")
            path_prefix: Optional path prefix (e.g., "uploads/user123/2025/01")
            
        Returns:
            Public URL to uploaded file
        """
        try:
            # Generate unique filename to avoid collisions
            unique_id = uuid.uuid4().hex[:12]
            unique_filename = f"{unique_id}_{filename}"
            
            # Build full object path
            if path_prefix:
                # Remove leading/trailing slashes
                path_prefix = path_prefix.strip("/")
                object_name = f"{path_prefix}/{unique_filename}"
            else:
                object_name = unique_filename
            
            # Create BytesIO stream from bytes
            file_stream = BytesIO(file_data)
            file_size = len(file_data)
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=object_name,
                data=file_stream,
                length=file_size,
                content_type=content_type,
            )
            
            # Generate public URL
            protocol = "https" if self.secure else "http"
            url = f"{protocol}://{self.endpoint}/{self.bucket}/{object_name}"
            
            logger.info(f"✓ Uploaded file: {object_name} ({file_size} bytes)")
            
            return url
            
        except S3Error as e:
            logger.error(f"Failed to upload file: {e}")
            raise RuntimeError(f"File upload failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            raise RuntimeError(f"File upload failed: {str(e)}")
    
    async def get_presigned_url(
        self,
        object_name: str,
        expires_seconds: int = 3600,
    ) -> str:
        """
        Get pre-signed URL for temporary file access.
        Useful for private files that need temporary public access.
        
        Args:
            object_name: Object path in bucket (e.g., "uploads/user123/file.jpg")
            expires_seconds: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Pre-signed URL string
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket,
                object_name=object_name,
                expires=timedelta(seconds=expires_seconds),
            )
            
            logger.debug(f"Generated pre-signed URL for: {object_name}")
            
            return url
            
        except S3Error as e:
            logger.error(f"Failed to generate pre-signed URL: {e}")
            raise RuntimeError(f"URL generation failed: {str(e)}")
    
    async def delete_file(self, object_name: str) -> bool:
        """
        Delete file from MinIO.
        
        Args:
            object_name: Object path in bucket
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket,
                object_name=object_name,
            )
            
            logger.info(f"✓ Deleted file: {object_name}")
            
            return True
            
        except S3Error as e:
            logger.error(f"Failed to delete file {object_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during deletion: {e}")
            return False
    
    async def file_exists(self, object_name: str) -> bool:
        """
        Check if file exists in MinIO.
        
        Args:
            object_name: Object path in bucket
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.stat_object(
                bucket_name=self.bucket,
                object_name=object_name,
            )
            return True
        except S3Error:
            return False
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False
    
    def get_object_name_from_url(self, url: str) -> Optional[str]:
        """
        Extract object name from MinIO URL.
        
        Args:
            url: Full MinIO URL
            
        Returns:
            Object name or None if invalid URL
        """
        try:
            # URL format: http://localhost:9000/bucket-name/path/to/file.jpg
            parts = url.split(f"/{self.bucket}/")
            if len(parts) == 2:
                return parts[1]
            return None
        except Exception:
            return None
    
    async def download_file(self, object_name: str) -> Optional[bytes]:
        """
        Download file from MinIO.
        
        Args:
            object_name: Object path in bucket
            
        Returns:
            File bytes or None if error
        """
        try:
            response = self.client.get_object(
                bucket_name=self.bucket,
                object_name=object_name,
            )
            
            file_data = response.read()
            response.close()
            response.release_conn()
            
            logger.debug(f"Downloaded file: {object_name} ({len(file_data)} bytes)")
            
            return file_data
            
        except S3Error as e:
            logger.error(f"Failed to download file {object_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            return None
    
    async def get_file_info(self, object_name: str) -> Optional[dict]:
        """
        Get file metadata/info.
        
        Args:
            object_name: Object path in bucket
            
        Returns:
            Dict with file info or None if not found
        """
        try:
            stat = self.client.stat_object(
                bucket_name=self.bucket,
                object_name=object_name,
            )
            
            return {
                "object_name": object_name,
                "size": stat.size,
                "content_type": stat.content_type,
                "etag": stat.etag,
                "last_modified": stat.last_modified,
                "metadata": stat.metadata,
            }
            
        except S3Error as e:
            logger.error(f"Failed to get file info for {object_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting file info: {e}")
            return None
    
    async def list_files(
        self,
        prefix: Optional[str] = None,
        max_results: int = 1000,
    ) -> list:
        """
        List files in bucket.
        
        Args:
            prefix: Filter by prefix (e.g., "uploads/user123/")
            max_results: Maximum number of results
            
        Returns:
            List of file info dicts
        """
        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket,
                prefix=prefix or "",
                recursive=True,
            )
            
            files = []
            for obj in objects:
                if len(files) >= max_results:
                    break
                
                files.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                })
            
            logger.debug(f"Listed {len(files)} files (prefix: {prefix})")
            
            return files
            
        except S3Error as e:
            logger.error(f"Failed to list files: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing files: {e}")
            return []
    
    async def copy_file(
        self,
        source_object: str,
        destination_object: str,
    ) -> bool:
        """
        Copy file within bucket.
        
        Args:
            source_object: Source object path
            destination_object: Destination object path
            
        Returns:
            True if copied successfully
        """
        try:
            from minio.commonconfig import CopySource
            
            self.client.copy_object(
                bucket_name=self.bucket,
                object_name=destination_object,
                source=CopySource(self.bucket, source_object),
            )
            
            logger.info(f"✓ Copied file: {source_object} → {destination_object}")
            
            return True
            
        except S3Error as e:
            logger.error(f"Failed to copy file: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error copying file: {e}")
            return False
    
    async def get_bucket_stats(self) -> dict:
        """
        Get bucket statistics.
        
        Returns:
            Dict with bucket stats (total files, total size, etc.)
        """
        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket,
                recursive=True,
            )
            
            total_files = 0
            total_size = 0
            
            for obj in objects:
                total_files += 1
                total_size += obj.size
            
            # Format size
            size_mb = total_size / (1024 * 1024)
            size_gb = size_mb / 1024
            
            if size_gb >= 1:
                size_str = f"{size_gb:.2f} GB"
            else:
                size_str = f"{size_mb:.2f} MB"
            
            return {
                "bucket": self.bucket,
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_formatted": size_str,
            }
            
        except S3Error as e:
            logger.error(f"Failed to get bucket stats: {e}")
            return {
                "bucket": self.bucket,
                "total_files": 0,
                "total_size_bytes": 0,
                "error": str(e),
            }
    
    async def health_check(self) -> dict:
        """
        Check MinIO connection health.
        
        Returns:
            Dict with health status
        """
        try:
            # Check if bucket exists (tests connection)
            exists = self.client.bucket_exists(self.bucket)
            
            if exists:
                # Try to list objects (tests read permission)
                # Just get first object to verify we can list
                try:
                    next(self.client.list_objects(self.bucket, recursive=False), None)
                    can_list = True
                except Exception:
                    can_list = False
                
                return {
                    "status": "healthy",
                    "bucket": self.bucket,
                    "endpoint": self.endpoint,
                    "bucket_exists": True,
                    "can_list": can_list,
                }
            else:
                return {
                    "status": "unhealthy",
                    "bucket": self.bucket,
                    "endpoint": self.endpoint,
                    "bucket_exists": False,
                    "error": f"Bucket {self.bucket} does not exist",
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "bucket": self.bucket,
                "endpoint": self.endpoint,
                "error": str(e),
            }


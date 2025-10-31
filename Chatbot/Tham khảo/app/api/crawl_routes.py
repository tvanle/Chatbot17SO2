"""
Web crawling routes for extracting content from URLs.
Protected by JWT authentication - requires ADMIN role.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from app.api.auth_dependencies import get_current_admin_user
from app.application.factory import ProviderFactory
from app.application.services import RAGService
from app.core.mongodb_models import UserInDB
from app.infrastructure.tools.firecrawl_crawler import FireCrawlCrawler

router = APIRouter(prefix="/crawl", tags=["crawl"])


class ScrapeRequest(BaseModel):
    """Request model for scraping a single URL."""
    
    url: HttpUrl
    collection: str = "web_content"
    only_main_content: bool = True
    auto_ingest: bool = True  # Automatically ingest into RAG


class ScrapeResponse(BaseModel):
    """Response model for scrape operation."""
    
    success: bool
    url: str
    markdown: Optional[str] = None
    content_length: Optional[int] = None
    duration_seconds: float
    error: Optional[str] = None
    ingested: bool = False
    doc_id: Optional[str] = None
    chunk_count: Optional[int] = None


class CrawlRequest(BaseModel):
    """Request model for crawling a URL and its linked pages."""
    
    url: HttpUrl
    max_depth: int = 2
    limit: int = 10
    collection: str = "web_content"
    auto_ingest: bool = True


class CrawlResponse(BaseModel):
    """Response model for crawl operation."""
    
    success: bool
    url: str
    total_pages: int = 0
    ingested_pages: int = 0
    duration_seconds: float
    error: Optional[str] = None


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(
    request: ScrapeRequest,
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    Scrape a single URL and optionally ingest into RAG system.
    Admin only.
    
    - Extracts main content as markdown
    - Validates and cleans content
    - Optionally ingests into vector database
    """
    try:
        # Initialize crawler
        crawler = FireCrawlCrawler()
        
        # Scrape URL
        result = await crawler.scrape_url(
            url=str(request.url),
            only_main_content=request.only_main_content,
        )
        
        if not result["success"]:
            return ScrapeResponse(
                success=False,
                url=str(request.url),
                duration_seconds=result["duration_seconds"],
                error=result.get("error"),
            )
        
        # Prepare response
        response = ScrapeResponse(
            success=True,
            url=result["url"],
            markdown=result["markdown"],
            content_length=result["content_length"],
            duration_seconds=result["duration_seconds"],
        )
        
        # Auto-ingest if requested
        if request.auto_ingest:
            try:
                # Get RAG service
                embedding = ProviderFactory.get_embedding_provider()
                llm = ProviderFactory.get_llm_provider()
                vector_store = await ProviderFactory.get_vector_store()
                mongodb = await ProviderFactory.get_mongodb_client()
                
                from app.application.services import DocumentService
                processor = ProviderFactory.get_document_processor()
                doc_service = DocumentService(processor)
                
                cache = await ProviderFactory.get_redis_client() if True else None
                rag_service = RAGService(embedding, llm, vector_store, doc_service, cache)
                
                # Ingest content
                result_metadata = result.get("metadata", {})
                if not isinstance(result_metadata, dict):
                    result_metadata = {}
                
                metadata = {
                    "source": "web_scrape",
                    "url": result["url"],
                    "scraped_by": current_admin.username,
                    "title": result_metadata.get("title", result["url"]) if result_metadata else result["url"],
                }
                
                ingest_result = await rag_service.ingest_text(
                    text=result["markdown"],
                    metadata=metadata,
                    collection=request.collection,
                )
                
                response.ingested = True
                response.doc_id = ingest_result.get("doc_ids", [None])[0]
                response.chunk_count = ingest_result.get("chunk_count", 0)
                
            except Exception as e:
                # Don't fail the whole request if ingestion fails
                response.error = f"Scrape succeeded but ingestion failed: {str(e)}"
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scrape failed: {str(e)}",
        )


@router.post("/crawl", response_model=CrawlResponse)
async def crawl_url(
    request: CrawlRequest,
    current_admin: UserInDB = Depends(get_current_admin_user),
):
    """
    Crawl a URL and its linked pages, optionally ingesting all into RAG.
    Admin only.
    
    - Crawls starting URL and follows links up to max_depth
    - Extracts content from up to 'limit' pages
    - Optionally ingests all pages into vector database
    """
    try:
        # Initialize crawler
        crawler = FireCrawlCrawler()
        
        # Crawl URL
        result = await crawler.crawl_url(
            url=str(request.url),
            max_depth=request.max_depth,
            limit=request.limit,
        )
        
        if not result["success"]:
            return CrawlResponse(
                success=False,
                url=str(request.url),
                duration_seconds=result["duration_seconds"],
                error=result.get("error"),
            )
        
        total_pages = result["total_pages"]
        ingested_pages = 0
        
        # Auto-ingest if requested
        if request.auto_ingest and result.get("pages"):
            try:
                # Get RAG service
                embedding = ProviderFactory.get_embedding_provider()
                llm = ProviderFactory.get_llm_provider()
                vector_store = await ProviderFactory.get_vector_store()
                
                from app.application.services import DocumentService
                processor = ProviderFactory.get_document_processor()
                doc_service = DocumentService(processor)
                
                cache = await ProviderFactory.get_redis_client() if True else None
                rag_service = RAGService(embedding, llm, vector_store, doc_service, cache)
                
                # Ingest each page
                for page in result["pages"]:
                    try:
                        # Handle page as object or dict
                        if hasattr(page, 'markdown'):
                            markdown = page.markdown
                            page_url = page.url if hasattr(page, 'url') else str(request.url)
                            page_metadata = page.metadata if hasattr(page, 'metadata') else {}
                        else:
                            markdown = page.get("markdown", "")
                            page_url = page.get("url", str(request.url))
                            page_metadata = page.get("metadata", {})
                        
                        if not markdown:
                            continue
                        
                        if not isinstance(page_metadata, dict):
                            page_metadata = {}
                        
                        metadata = {
                            "source": "web_crawl",
                            "url": page_url,
                            "crawled_by": current_admin.username,
                            "title": page_metadata.get("title", "") if page_metadata else "",
                        }
                        
                        await rag_service.ingest_text(
                            text=markdown,
                            metadata=metadata,
                            collection=request.collection,
                        )
                        
                        ingested_pages += 1
                        
                    except Exception as e:
                        # Continue with other pages if one fails
                        continue
                        
            except Exception as e:
                # Don't fail if ingestion has issues
                pass
        
        return CrawlResponse(
            success=True,
            url=str(request.url),
            total_pages=total_pages,
            ingested_pages=ingested_pages,
            duration_seconds=result["duration_seconds"],
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Crawl failed: {str(e)}",
        )


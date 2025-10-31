"""
FireCrawl crawler for extracting web content.
Uses FireCrawl API to crawl and extract content from URLs.
"""

import logging
import time
from typing import Any, Dict, Optional

from firecrawl import FirecrawlApp

from app.config.settings import settings

logger = logging.getLogger(__name__)


class FireCrawlCrawler:
    """Crawler using FireCrawl API to extract content from URLs."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the crawler.
        
        Args:
            api_key: Firecrawl API key (defaults to settings)
        """
        self.api_key = api_key or settings.firecrawl_api_key
        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY is required")
            
        self.client = FirecrawlApp(api_key=self.api_key)
        self.timeout = 60000  # 60 seconds
        self.min_content_length = 100

    async def scrape_url(
        self,
        url: str,
        formats: list[str] = None,
        only_main_content: bool = True
    ) -> Dict[str, Any]:
        """
        Scrape a single URL and extract content.
        
        Args:
            url: URL to scrape
            formats: Output formats (default: ["markdown"])
            only_main_content: Extract only main content (default: True)
            
        Returns:
            Dictionary with scraped data including markdown content
        """
        start_time = time.time()
        
        try:
            logger.info(f"Scraping URL: {url}")
            
            # Scrape using Firecrawl
            result = self.client.scrape(
                url,
                formats=formats or ["markdown"],
                only_main_content=only_main_content,
                timeout=self.timeout,
            )
            
            duration = time.time() - start_time
            
            if not result:
                raise Exception("Empty response from Firecrawl")
            
            # Extract markdown content
            markdown_content = result.markdown if hasattr(result, 'markdown') else result.get("markdown", "")
            
            # Validate content
            is_valid, error_msg = self.validate_content(markdown_content)
            if not is_valid:
                raise Exception(f"Invalid content: {error_msg}")
            
            # Clean content
            cleaned_content = self.clean_content(markdown_content)
            
            logger.info(
                f"Successfully scraped {url} in {duration:.2f}s "
                f"({len(cleaned_content)} chars)"
            )
            
            metadata = result.metadata if hasattr(result, 'metadata') else result.get("metadata", {})
            
            return {
                "success": True,
                "url": url,
                "markdown": cleaned_content,
                "metadata": metadata,
                "duration_seconds": duration,
                "content_length": len(cleaned_content),
            }
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to scrape {url}: {str(e)}")
            
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "duration_seconds": duration,
            }

    async def crawl_url(
        self,
        url: str,
        max_depth: int = 2,
        limit: int = 10,
        formats: list[str] = None,
    ) -> Dict[str, Any]:
        """
        Crawl a URL and its linked pages.
        
        Args:
            url: Starting URL
            max_depth: Maximum crawl depth
            limit: Maximum number of pages to crawl
            formats: Output formats
            
        Returns:
            Dictionary with crawl results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting crawl from: {url} (max_depth={max_depth}, limit={limit})")
            
            # Create scrape options
            from firecrawl.v2.types import ScrapeOptions
            scrape_opts = ScrapeOptions(
                formats=formats or ["markdown"],
                only_main_content=True,
                timeout=self.timeout,
            )
            
            # Start crawl job (async mode)
            result = self.client.crawl(
                url,
                limit=limit,
                max_discovery_depth=max_depth,
                scrape_options=scrape_opts,
                poll_interval=5,
            )
            
            duration = time.time() - start_time
            
            # Extract pages from result
            pages = result.data if hasattr(result, 'data') else []
            total_pages = len(pages)
            
            logger.info(
                f"Crawl completed in {duration:.2f}s, found {total_pages} pages"
            )
            
            return {
                "success": True,
                "url": url,
                "total_pages": total_pages,
                "pages": pages,
                "duration_seconds": duration,
            }
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to crawl {url}: {str(e)}")
            
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "duration_seconds": duration,
            }

    def validate_content(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Validate extracted content.

        Returns:
            (is_valid, error_message)
        """
        if not content:
            return False, "Empty content"

        # Check minimum length
        if len(content) < self.min_content_length:
            return False, f"Content too short ({len(content)} chars)"

        # Check for common error pages
        error_indicators = [
            "404 not found",
            "page not found",
            "access denied",
            "forbidden",
            "error 404",
            "500 internal server error",
        ]

        content_lower = content.lower()
        for indicator in error_indicators:
            if indicator in content_lower[:500]:  # Check first 500 chars
                return False, f"Detected error page: {indicator}"

        return True, None

    async def search_web(
        self,
        query: str,
        max_results: int = 5,
        formats: list[str] = None,
    ) -> Dict[str, Any]:
        """
        Search the web using Firecrawl.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            formats: Output formats
            
        Returns:
            Dictionary with search results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Searching web for: {query}")
            
            # Create scrape options for search results
            from firecrawl.v2.types import ScrapeOptions
            scrape_opts = ScrapeOptions(
                formats=formats or ["markdown"],
                only_main_content=True,
            )
            
            # Search using Firecrawl
            result = self.client.search(
                query,
                limit=max_results,
                scrape_options=scrape_opts,
            )
            
            duration = time.time() - start_time
            
            if not result:
                raise Exception("No results returned from search")
            
            # Extract search results (Firecrawl returns web, news, images)
            results = []
            if hasattr(result, 'web') and result.web:
                results = result.web
            elif hasattr(result, 'news') and result.news:
                results = result.news
            else:
                results = []
            
            # Process each result
            processed_results = []
            for item in results:
                try:
                    # Extract content
                    if hasattr(item, 'markdown'):
                        markdown = item.markdown
                        url = item.url if hasattr(item, 'url') else ""
                        title = item.metadata.title if hasattr(item, 'metadata') and hasattr(item.metadata, 'title') else ""
                    else:
                        markdown = item.get("markdown", "")
                        url = item.get("url", "")
                        metadata = item.get("metadata", {})
                        title = metadata.get("title", "") if isinstance(metadata, dict) else ""
                    
                    # Validate and clean
                    is_valid, error_msg = self.validate_content(markdown)
                    if not is_valid:
                        continue
                    
                    cleaned = self.clean_content(markdown)
                    
                    processed_results.append({
                        "url": url,
                        "title": title,
                        "content": cleaned,
                        "length": len(cleaned),
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to process search result: {e}")
                    continue
            
            logger.info(
                f"Search completed in {duration:.2f}s, found {len(processed_results)} valid results"
            )
            
            return {
                "success": True,
                "query": query,
                "results": processed_results,
                "total_results": len(processed_results),
                "duration_seconds": duration,
            }
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to search web for '{query}': {str(e)}")
            
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "duration_seconds": duration,
            }

    def clean_content(self, content: str) -> str:
        """Clean and normalize extracted content."""
        if not content:
            return ""

        # Remove excessive whitespace
        lines = content.split("\n")
        cleaned_lines = []

        prev_empty = False
        for line in lines:
            line = line.rstrip()

            if not line:
                if not prev_empty:
                    cleaned_lines.append("")
                prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False

        # Join lines
        cleaned = "\n".join(cleaned_lines)

        # Remove more than 2 consecutive newlines
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")

        return cleaned.strip()

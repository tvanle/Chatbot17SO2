"""
Web Search Service for integrating real-time web search into RAG pipeline.
Follows Single Responsibility Principle - only handles web search orchestration.
"""

import logging
from typing import Dict, List, Optional

from app.core.models import WebSearchConfig
from app.infrastructure.tools.firecrawl_crawler import FireCrawlCrawler

logger = logging.getLogger(__name__)


class WebSearchService:
    """
    Service for web search integration with RAG.
    Follows SRP: Only responsible for coordinating web search operations.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize web search service.
        
        Args:
            api_key: Firecrawl API key (optional, defaults to settings)
        """
        self.crawler = FireCrawlCrawler(api_key=api_key)

    async def search(
        self,
        query: str,
        config: WebSearchConfig,
    ) -> Dict:
        """
        Search the web and return structured results.
        
        Args:
            query: Search query
            config: Web search configuration
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            logger.info(f"Web search initiated: {query}")
            
            # Perform web search
            result = await self.crawler.search_web(
                query=query,
                max_results=config.max_results,
                formats=config.formats,
            )
            
            if not result["success"]:
                logger.warning(f"Web search failed: {result.get('error')}")
                return {
                    "success": False,
                    "query": query,
                    "results": [],
                    "error": result.get("error"),
                }
            
            # Extract and format results
            search_results = result.get("results", [])
            
            logger.info(
                f"Web search completed: {len(search_results)} results in "
                f"{result['duration_seconds']:.2f}s"
            )
            
            return {
                "success": True,
                "query": query,
                "results": search_results,
                "total_results": len(search_results),
                "duration_seconds": result["duration_seconds"],
            }
            
        except Exception as e:
            logger.error(f"Web search service error: {e}")
            return {
                "success": False,
                "query": query,
                "results": [],
                "error": str(e),
            }

    def format_results_for_context(self, results: List[Dict]) -> str:
        """
        Format search results as context for LLM.
        
        Args:
            results: List of search results
            
        Returns:
            Formatted string for use as context
        """
        if not results:
            return ""
        
        context_parts = ["# Web Search Results\n"]
        
        for idx, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            content = result.get("content", "")
            
            # Truncate content if too long (keep first 1000 chars per result)
            if len(content) > 1000:
                content = content[:1000] + "..."
            
            context_parts.append(f"\n## Source {idx}: {title}")
            if url:
                context_parts.append(f"URL: {url}")
            context_parts.append(f"\n{content}\n")
            context_parts.append("---")
        
        return "\n".join(context_parts)

    def create_web_sources(self, results: List[Dict]) -> List[Dict]:
        """
        Create source citations from search results.
        
        Args:
            results: List of search results
            
        Returns:
            List of source dictionaries for response
        """
        sources = []
        
        for idx, result in enumerate(results, 1):
            sources.append({
                "id": f"web_{idx}",
                "title": result.get("title", "Untitled"),
                "url": result.get("url", ""),
                "content_preview": result.get("content", "")[:200] + "...",
                "source_type": "web_search",
            })
        
        return sources


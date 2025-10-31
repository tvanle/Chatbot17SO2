"""
Data crawler service for orchestrating web crawling operations.
Coordinates CSV parsing, crawling, and saving results.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.core.models import CrawlBatchReport, CrawlResult, CrawlStatus, CrawlTask
from app.infrastructure.tools.csv_parser import DataSheetParser
from app.infrastructure.tools.firecrawl_crawler import FireCrawlCrawler

logger = logging.getLogger(__name__)


class DataCrawlerService:
    """Service for crawling and processing web data."""

    def __init__(
        self,
        csv_path: str = "assets/data_sheet.csv",
        output_dir: str = "assets/raw",
        force_recrawl: bool = False,
    ):
        """
        Initialize the data crawler service.

        Args:
            csv_path: Path to CSV file
            output_dir: Directory to save crawled files
            force_recrawl: If True, recrawl even if file exists
        """
        self.csv_path = csv_path
        self.output_dir = Path(output_dir)
        self.force_recrawl = force_recrawl

        self.parser = DataSheetParser(csv_path)
        self.crawler = FireCrawlCrawler()

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_tasks(self) -> List[CrawlTask]:
        """Get list of crawl tasks from CSV."""
        tasks = self.parser.parse()

        if not self.force_recrawl:
            # Filter out tasks that already have files
            filtered_tasks = []
            for task in tasks:
                output_path = self.output_dir / task.output_filename
                if output_path.exists():
                    logger.info(f"Skipping {task.title} - file already exists")
                    task.status = CrawlStatus.SKIPPED
                else:
                    filtered_tasks.append(task)
            tasks = filtered_tasks

        return tasks

    def save_result(self, result: CrawlResult) -> bool:
        """
        Save crawl result to file.

        Returns:
            True if saved successfully
        """
        if not result.success or not result.content:
            return False

        try:
            output_path = self.output_dir / result.task.output_filename

            # Clean content
            cleaned_content = self.crawler.clean_content(result.content)

            # Save to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(cleaned_content)

            result.saved_path = str(output_path)
            logger.info(f"Saved to {output_path} ({len(cleaned_content)} bytes)")

            return True

        except Exception as e:
            logger.error(f"Failed to save result: {str(e)}")
            result.error = f"Save failed: {str(e)}"
            return False

    def create_report(
        self, results: List[CrawlResult], duration: float
    ) -> CrawlBatchReport:
        """Create batch report from results."""
        total = len(results)
        completed = sum(1 for r in results if r.success)
        failed = sum(
            1 for r in results if not r.success and r.task.status == CrawlStatus.FAILED
        )
        skipped = sum(1 for r in results if r.task.status == CrawlStatus.SKIPPED)

        return CrawlBatchReport(
            total_tasks=total,
            completed=completed,
            failed=failed,
            skipped=skipped,
            duration_seconds=duration,
            results=results,
            timestamp=datetime.now(),
        )

    def print_statistics(self):
        """Print statistics about the data sheet."""
        stats = self.parser.get_statistics()

        print("\n" + "=" * 60)
        print("DATA SHEET STATISTICS")
        print("=" * 60)
        print(f"Total rows:           {stats['total_rows']}")
        print(f"Rows with URL:        {stats['has_url']}")
        print(f"Rows with text:       {stats['has_text']}")
        print(f"Rows need crawling:   {stats['needs_crawl']}")
        print("=" * 60 + "\n")

    def print_report(self, report: CrawlBatchReport):
        """Print crawl batch report."""
        print("\n" + "=" * 60)
        print("CRAWL REPORT")
        print("=" * 60)
        print(f"Total tasks:     {report.total_tasks}")
        print(f"✓ Completed:     {report.completed}")
        print(f"✗ Failed:        {report.failed}")
        print(f"⊘ Skipped:       {report.skipped}")
        print(f"Duration:        {report.duration_seconds:.2f}s")
        print("=" * 60)

        if report.failed > 0:
            print("\nFAILED TASKS:")
            for result in report.results:
                if not result.success and result.task.status == CrawlStatus.FAILED:
                    print(f"  ✗ {result.task.title}")
                    print(f"    URL: {result.task.url}")
                    print(f"    Error: {result.error}")

        if report.completed > 0:
            print(f"\nSUCCESSFUL CRAWLS:")
            for result in report.results:
                if result.success:
                    print(f"  ✓ {result.task.title}")
                    print(f"    File: {result.saved_path}")
                    print(f"    Size: {result.content_length} chars")

        print("\n" + "=" * 60 + "\n")

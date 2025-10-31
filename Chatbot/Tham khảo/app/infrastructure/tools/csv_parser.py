"""
CSV parser for extracting crawl tasks from data sheet.
Parses CSV file and generates CrawlTask objects for URLs that need crawling.
"""

import re
from pathlib import Path
from typing import List, Optional

import pandas as pd

from app.core.models import CrawlStatus, CrawlTask


class DataSheetParser:
    """Parser for data_sheet.csv to extract crawl tasks."""

    def __init__(self, csv_path: str = "assets/data_sheet.csv"):
        self.csv_path = Path(csv_path)
        self.df: Optional[pd.DataFrame] = None

    def parse(self) -> List[CrawlTask]:
        """Parse CSV and extract crawl tasks."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        self.df = pd.read_csv(self.csv_path, encoding="utf-8")
        tasks = []

        for idx, row in self.df.iterrows():
            task = self._parse_row(row, idx)
            if task:
                tasks.append(task)

        return tasks

    def _parse_row(self, row: pd.Series, idx: int) -> Optional[CrawlTask]:
        """Parse single CSV row into CrawlTask."""
        url = self._get_value(row, "Link (Nếu Có)")
        ban_text = self._get_value(row, "Bản text")

        # Skip if no URL or already has text file
        if not url or ban_text:
            return None

        # Skip if URL is not valid
        if not self._is_valid_url(url):
            return None

        # Extract data
        title = self._get_value(row, "Dữ Liệu", f"Document_{idx}")
        nguon = self._get_value(row, "Nguồn Dữ Liệu", "")
        phan_loai = self._get_value(row, "Phân Loại", "")
        nhan = self._get_value(row, "Nhãn", "")

        # Generate filename from title
        filename = self._sanitize_filename(title)

        # Build metadata
        metadata = {
            "source": nguon,
            "category": phan_loai,
            "label": nhan,
            "csv_index": idx,
        }

        return CrawlTask(
            url=url.strip(),
            title=title,
            metadata=metadata,
            output_filename=filename,
            status=CrawlStatus.PENDING,
        )

    def _get_value(self, row: pd.Series, column: str, default: str = "") -> str:
        """Get value from row safely."""
        try:
            val = row.get(column, default)
            if pd.isna(val):
                return default
            return str(val).strip()
        except Exception:
            return default

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        if not url or pd.isna(url):
            return False
        url = url.strip().lower()
        return url.startswith("http://") or url.startswith("https://")

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title to create valid filename."""
        # Remove or replace invalid filename characters
        # Keep Vietnamese characters
        filename = title.strip()

        # Replace problematic characters
        replacements = {
            "/": "-",
            "\\": "-",
            ":": "-",
            "*": "",
            "?": "",
            '"': "",
            "<": "",
            ">": "",
            "|": "",
            "\n": " ",
            "\r": " ",
            "\t": " ",
        }

        for old, new in replacements.items():
            filename = filename.replace(old, new)

        # Replace multiple spaces with single space
        filename = re.sub(r"\s+", " ", filename)

        # Trim to reasonable length
        if len(filename) > 200:
            filename = filename[:200]

        filename = filename.strip()

        # Add .md extension
        if not filename.endswith(".md"):
            filename += ".md"

        return filename

    def get_statistics(self) -> dict:
        """Get statistics about the CSV data."""
        if self.df is None:
            self.df = pd.read_csv(self.csv_path, encoding="utf-8")

        total_rows = len(self.df)
        has_url = self.df["Link (Nếu Có)"].notna().sum()
        has_text = self.df["Bản text"].notna().sum()
        needs_crawl = (
            self.df["Link (Nếu Có)"].notna() & self.df["Bản text"].isna()
        ).sum()

        return {
            "total_rows": total_rows,
            "has_url": int(has_url),
            "has_text": int(has_text),
            "needs_crawl": int(needs_crawl),
        }

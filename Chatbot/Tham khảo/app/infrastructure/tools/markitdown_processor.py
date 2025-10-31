"""
Document processor using markitdown.
Converts various file formats to markdown text.
"""

from markitdown import MarkItDown

from app.core.interfaces import IDocumentProcessor


class MarkItDownProcessor(IDocumentProcessor):
    """Document processor using markitdown."""

    def __init__(self):
        self.converter = MarkItDown()

    async def process(self, file_path: str) -> str:
        result = self.converter.convert(file_path)
        return result.text_content

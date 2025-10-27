"""
Text chunking utilities for splitting documents into smaller pieces
"""
from typing import List
import re


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    separator: str = "\n\n"
) -> List[str]:
    """
    Split text into chunks with overlap

    Args:
        text: Input text to split
        chunk_size: Maximum characters per chunk
        chunk_overlap: Number of overlapping characters between chunks
        separator: Primary separator to split on (paragraphs by default)

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    # First, try to split by separator (paragraphs)
    paragraphs = text.split(separator)

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If adding this paragraph exceeds chunk_size
        if len(current_chunk) + len(para) + len(separator) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                # Add overlap from the end of current chunk
                overlap_text = current_chunk[-chunk_overlap:] if chunk_overlap > 0 else ""
                current_chunk = overlap_text + separator + para
            else:
                # Single paragraph is too large, split it by sentences
                sentences = split_into_sentences(para)
                temp_chunk = ""
                for sent in sentences:
                    if len(temp_chunk) + len(sent) > chunk_size:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                            overlap_text = temp_chunk[-chunk_overlap:] if chunk_overlap > 0 else ""
                            temp_chunk = overlap_text + " " + sent
                        else:
                            # Even single sentence is too large, hard split
                            chunks.append(sent[:chunk_size])
                            temp_chunk = sent[chunk_size - chunk_overlap:] if len(sent) > chunk_size else ""
                    else:
                        temp_chunk += " " + sent if temp_chunk else sent

                if temp_chunk:
                    current_chunk = temp_chunk
        else:
            current_chunk += separator + para if current_chunk else para

    # Add the last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences (Vietnamese and English support)
    """
    # Simple sentence splitter (can be improved with NLP libraries)
    sentence_endings = re.compile(r'([.!?;])\s+')
    sentences = sentence_endings.split(text)

    # Recombine sentences with their punctuation
    result = []
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")
        if sentence.strip():
            result.append(sentence.strip())

    # Add last sentence if exists
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1].strip())

    return result if result else [text]


def chunk_by_tokens(
    text: str,
    max_tokens: int = 256,
    overlap_tokens: int = 20,
    estimate_ratio: float = 0.25
) -> List[str]:
    """
    Chunk text by token count (using character estimation)

    Args:
        text: Input text
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Overlapping tokens
        estimate_ratio: Ratio to estimate tokens from characters (1 token ≈ 4 chars)

    Returns:
        List of chunks
    """
    # Rough estimation: 1 token ≈ 4 characters
    chars_per_token = int(1 / estimate_ratio)
    max_chars = max_tokens * chars_per_token
    overlap_chars = overlap_tokens * chars_per_token

    return chunk_text(text, chunk_size=max_chars, chunk_overlap=overlap_chars)

"""
Token counting utilities for text
"""
from typing import List, Optional


def count_tokens(text: str, method: str = "estimate") -> int:
    """
    Count tokens in text

    Args:
        text: Input text
        method: "estimate" (fast approximation) or "tiktoken" (accurate but requires library)

    Returns:
        Estimated token count
    """
    if method == "estimate":
        return estimate_tokens(text)
    elif method == "tiktoken":
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
            return len(encoding.encode(text))
        except ImportError:
            # Fallback to estimation if tiktoken not installed
            return estimate_tokens(text)
    else:
        return estimate_tokens(text)


def estimate_tokens(text: str) -> int:
    """
    Fast token estimation without external libraries
    Rough rule: 1 token ≈ 4 characters (for English)
    For Vietnamese: 1 token ≈ 3-4 characters

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Simple heuristic: split by whitespace and punctuation
    words = text.split()

    # Average: 1 word ≈ 1.3 tokens (accounting for subword tokenization)
    estimated_tokens = int(len(words) * 1.3)

    return estimated_tokens


def fit_within_budget(texts: List[str], token_budget: int) -> List[str]:
    """
    Select texts that fit within a token budget

    Args:
        texts: List of text strings
        token_budget: Maximum total tokens allowed

    Returns:
        Subset of texts that fit within budget
    """
    result = []
    total_tokens = 0

    for text in texts:
        text_tokens = estimate_tokens(text)
        if total_tokens + text_tokens <= token_budget:
            result.append(text)
            total_tokens += text_tokens
        else:
            # If we can fit a partial text, truncate it
            remaining = token_budget - total_tokens
            if remaining > 50:  # Only if we have meaningful space left
                # Approximate character count for remaining tokens
                chars_remaining = int(remaining / 1.3 * 5)  # rough conversion
                result.append(text[:chars_remaining] + "...")
            break

    return result


def count_tokens_batch(texts: List[str]) -> List[int]:
    """
    Count tokens for a batch of texts

    Args:
        texts: List of texts

    Returns:
        List of token counts
    """
    return [estimate_tokens(text) for text in texts]

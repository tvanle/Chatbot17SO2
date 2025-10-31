"""
Summarization Service for generating chat session titles and summaries.
Uses LLM to intelligently summarize conversation context.
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.interfaces import ILLMProvider
from app.core.mongodb_models import ChatMessageResponse

logger = logging.getLogger(__name__)


class SummarizationService:
    """
    Service for summarizing conversations and generating titles.
    Uses LLM to create concise, meaningful summaries.
    """

    def __init__(self, llm_provider: ILLMProvider):
        """
        Initialize summarization service.
        
        Args:
            llm_provider: LLM provider for generation
        """
        self.llm = llm_provider
        logger.info("SummarizationService initialized")

    async def generate_title(
        self,
        messages: List[ChatMessageResponse],
        max_length: int = 50,
    ) -> str:
        """
        Generate a concise title for a conversation based on its messages.
        
        Args:
            messages: List of chat messages
            max_length: Maximum title length
            
        Returns:
            Generated title string
        """
        try:
            if not messages:
                return "New Conversation"
            
            # Take first few messages for context (usually 2-4 messages)
            context_messages = messages[:4]
            
            # Build conversation context
            conversation = self._format_messages_for_context(context_messages)
            
            # System prompt for title generation
            system_prompt = """You are a helpful assistant that generates concise, descriptive titles for conversations.

Based on the conversation context provided, generate a short, meaningful title that captures the main topic or intent.

Rules:
- Maximum 6-8 words
- Be specific and descriptive
- Use natural language
- No quotation marks
- Capitalize appropriately
- Focus on the main topic or question

Example titles:
- "Implementing OAuth2 Authentication in FastAPI"
- "Debugging Memory Leak in Python Application"
- "Understanding Kubernetes Pod Networking"
- "Creating Custom React Hooks Tutorial"
"""
            
            # User prompt
            user_prompt = f"""Generate a title for this conversation:

{conversation}

Title (max {max_length} characters):"""
            
            # Generate title
            title = await self.llm.generate(
                prompt=user_prompt,
                context=system_prompt,
                temperature=0.7,
                max_tokens=50,
            )
            
            # Clean up title
            title = title.strip().strip('"').strip("'")
            
            # Truncate if too long
            if len(title) > max_length:
                title = title[:max_length].rsplit(" ", 1)[0] + "..."
            
            logger.debug(f"Generated title: {title}")
            
            return title
            
        except Exception as e:
            logger.error(f"Failed to generate title: {e}")
            # Fallback to simple title based on first user message
            return self._generate_fallback_title(messages, max_length)

    async def generate_summary(
        self,
        messages: List[ChatMessageResponse],
        max_length: int = 200,
    ) -> str:
        """
        Generate a summary of the conversation.
        
        Args:
            messages: List of chat messages
            max_length: Maximum summary length
            
        Returns:
            Generated summary string
        """
        try:
            if not messages:
                return "Empty conversation"
            
            # Build full conversation context
            conversation = self._format_messages_for_context(messages)
            
            # System prompt for summary generation
            system_prompt = """You are a helpful assistant that generates concise summaries of conversations.

Based on the conversation provided, create a brief summary that captures:
- The main topics discussed
- Key questions asked
- Important conclusions or insights

Rules:
- 2-3 sentences maximum
- Clear and informative
- Focus on key points
- Use natural language
"""
            
            # User prompt
            user_prompt = f"""Summarize this conversation in 2-3 sentences:

{conversation}

Summary:"""
            
            # Generate summary
            summary = await self.llm.generate(
                prompt=user_prompt,
                context=system_prompt,
                temperature=0.7,
                max_tokens=150,
            )
            
            # Clean up summary
            summary = summary.strip()
            
            # Truncate if too long
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(".", 1)[0] + "..."
            
            logger.debug(f"Generated summary: {summary}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return self._generate_fallback_summary(messages, max_length)

    async def should_generate_title(
        self,
        current_message_count: int,
        current_title: str,
    ) -> bool:
        """
        Determine if title should be auto-generated.
        
        Args:
            current_message_count: Number of messages in session
            current_title: Current session title
            
        Returns:
            True if title should be generated
        """
        # Generate title after 2-3 messages if still using default title
        if current_message_count >= 2 and current_title in ["New Conversation", "Untitled"]:
            return True
        
        return False

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _format_messages_for_context(
        self,
        messages: List[ChatMessageResponse],
    ) -> str:
        """
        Format messages into a readable conversation context.
        
        Args:
            messages: List of messages
            
        Returns:
            Formatted conversation string
        """
        lines = []
        
        for msg in messages:
            # Skip system messages in context
            if msg.role == "system":
                continue
            
            role_label = "User" if msg.role == "user" else "Assistant"
            
            # Truncate very long messages
            content = msg.content
            if len(content) > 500:
                content = content[:500] + "..."
            
            lines.append(f"{role_label}: {content}")
        
        return "\n\n".join(lines)

    def _generate_fallback_title(
        self,
        messages: List[ChatMessageResponse],
        max_length: int,
    ) -> str:
        """
        Generate a simple fallback title from first user message.
        
        Args:
            messages: List of messages
            max_length: Maximum length
            
        Returns:
            Fallback title
        """
        try:
            # Find first user message
            for msg in messages:
                if msg.role == "user":
                    # Take first sentence or first N characters
                    content = msg.content.strip()
                    
                    # Try to get first sentence
                    if "?" in content:
                        title = content.split("?")[0] + "?"
                    elif "." in content:
                        title = content.split(".")[0]
                    else:
                        title = content
                    
                    # Truncate
                    if len(title) > max_length:
                        title = title[:max_length].rsplit(" ", 1)[0] + "..."
                    
                    return title
            
            return "New Conversation"
            
        except Exception as e:
            logger.error(f"Failed to generate fallback title: {e}")
            return "New Conversation"

    def _generate_fallback_summary(
        self,
        messages: List[ChatMessageResponse],
        max_length: int,
    ) -> str:
        """
        Generate a simple fallback summary.
        
        Args:
            messages: List of messages
            max_length: Maximum length
            
        Returns:
            Fallback summary
        """
        try:
            message_count = len(messages)
            user_messages = [m for m in messages if m.role == "user"]
            
            if not user_messages:
                return f"Conversation with {message_count} messages"
            
            first_message = user_messages[0].content[:100]
            
            summary = f"Conversation about: {first_message}"
            
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate fallback summary: {e}")
            return "Conversation summary"


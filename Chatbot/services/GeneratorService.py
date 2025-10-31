"""
GeneratorService - Generates answers using LLM with retrieved context
Enhanced with conversation history support
"""
from typing import List, Optional, Dict
from Chatbot.services.ModelClient import ModelClient
from Chatbot.config.rag_config import get_rag_config


class GeneratorService:
    """
    Service for generating answers using LLM
    Combines user question with retrieved context chunks
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        max_tokens: Optional[int] = None,
        backend: Optional[str] = None
    ):
        """
        Initialize generator service

        Args:
            model_name: LLM model identifier (optional, uses config if None)
            max_tokens: Maximum tokens for generation (optional, uses config if None)
            backend: LLM backend (optional, uses config if None)
        """
        config = get_rag_config()
        self.client = ModelClient(
            model_name=model_name or config.llm_model,
            backend=backend or config.llm_backend
        )
        self.max_tokens = max_tokens or config.llm_max_tokens

    def generate(
        self,
        question: str,
        contexts: List[str],
        language: str = "vi",
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate answer to question using context chunks with conversation history

        Args:
            question: User's current question
            contexts: Retrieved context chunks (relevant text passages)
            language: Language for answer ("vi" or "en")
            conversation_history: Previous conversation turns in format:
                                 [{"role": "user|assistant", "content": "..."}]
                                 Will use last 10 messages to maintain context

        Returns:
            Generated answer
        """
        config = get_rag_config()

        # Build messages with conversation context
        messages = self._build_messages_with_context(
            question, contexts, language, conversation_history
        )

        # Generate answer using LLM with conversation history
        answer = self.client.complete(
            prompt=question,  # Not used when messages provided
            max_tokens=self.max_tokens,
            temperature=config.llm_temperature,
            messages=messages
        )

        return answer

    def _build_messages_with_context(
        self,
        question: str,
        contexts: List[str],
        language: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_history_turns: int = 10
    ) -> List[Dict[str, str]]:
        """
        Build messages array with system context, conversation history, and current question
        Following the reference implementation pattern for better conversational AI

        Args:
            question: Current user question
            contexts: Retrieved RAG context chunks
            language: Language for response
            conversation_history: Previous conversation messages
            max_history_turns: Maximum number of conversation turns to include

        Returns:
            List of messages in OpenAI chat format
        """
        messages = []

        # Step 1: Build system message with RAG context (optimized, shorter prompt)
        if language == "vi":
            system_content = (
                "Bạn là trợ lý AI của Học viện Công nghệ Bưu chính Viễn thông (PTIT). "
                "Sử dụng thông tin được cung cấp để trả lời câu hỏi một cách chính xác, đầy đủ và thân thiện.\n\n"
            )
        else:
            system_content = (
                "You are an AI assistant for PTIT (Posts and Telecommunications Institute of Technology). "
                "Use the provided information to answer questions accurately and comprehensively.\n\n"
            )

        # Add RAG retrieved context
        if contexts:
            if language == "vi":
                system_content += "=== THÔNG TIN THAM KHẢO ===\n\n"
            else:
                system_content += "=== REFERENCE INFORMATION ===\n\n"

            for i, ctx in enumerate(contexts, 1):
                system_content += f"[Nguồn {i}]: {ctx}\n\n"

            if language == "vi":
                system_content += (
                    "=== HƯỚng DẪN ===\n"
                    "- Trả lời dựa trên thông tin tham khảo trên\n"
                    "- Nếu câu hỏi về địa chỉ/liên hệ: liệt kê TẤT CẢ các địa điểm\n"
                    "- Sử dụng bullet points khi cần thiết\n"
                    "- Nếu thiếu thông tin: nói rõ và gợi ý cách tìm thêm\n"
                )
            else:
                system_content += (
                    "=== INSTRUCTIONS ===\n"
                    "- Answer based on the reference information above\n"
                    "- Use bullet points when appropriate\n"
                    "- If information is insufficient, clearly state that\n"
                )

        messages.append({"role": "system", "content": system_content})

        # Step 2: Add conversation history (last N turns for context window)
        if conversation_history:
            # Take only last N messages to avoid token limit
            recent_history = conversation_history[-max_history_turns:]

            # Add conversation history context marker
            if language == "vi":
                history_marker = "=== Lịch sử hội thoại trước đó ==="
            else:
                history_marker = "=== Previous conversation ==="

            messages.append({"role": "system", "content": history_marker})

            # Add each message from history
            for msg in recent_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content and role in ["user", "assistant"]:
                    messages.append({"role": role, "content": content})

            # Add instruction to use conversation context
            if language == "vi":
                context_instruction = (
                    "Sử dụng lịch sử hội thoại để hiểu ngữ cảnh và các đại từ tham chiếu "
                    "(như 'nó', 'đó', 'cái đó', 'địa chỉ trên')."
                )
            else:
                context_instruction = (
                    "Use the conversation history to understand context and references "
                    "(like 'it', 'that', 'the previous one')."
                )

            messages.append({"role": "system", "content": context_instruction})

        # Step 3: Add current user question
        messages.append({"role": "user", "content": question})

        return messages

    def _build_prompt(self, question: str, contexts: List[str], language: str) -> str:
        """
        Build RAG prompt with context injection

        Args:
            question: User's question
            contexts: Retrieved context chunks
            language: Language for prompt

        Returns:
            Formatted prompt string
        """
        if language == "vi":
            system_instruction = (
                "Bạn là trợ lý AI thông minh và thân thiện của Học viện Công nghệ Bưu chính Viễn thông (PTIT). "
                "Nhiệm vụ của bạn là trả lời câu hỏi một cách CHI TIẾT và DỄ HIỂU dựa trên các thông tin được cung cấp.\n\n"
                "QUY TẮC QUAN TRỌNG:\n"
                "1. Ưu tiên sử dụng thông tin từ tài liệu tham khảo bên dưới\n"
                "2. Trả lời đầy đủ, cụ thể với số liệu, địa chỉ, tên chính xác (nếu có)\n"
                "3. Nếu câu hỏi về địa chỉ/liên hệ: liệt kê TẤT CẢ các địa điểm liên quan\n"
                "4. Nếu thiếu thông tin: nói rõ phần nào chưa có, gợi ý cách tìm thêm\n"
                "5. Sử dụng format rõ ràng: bullet points, số thứ tự khi cần\n"
                "6. Giọng điệu chuyên nghiệp nhưng thân thiện\n"
                "7. Luôn dùng tiếng Việt có dấu chuẩn\n\n"
            )

            context_section = "THÔNG TIN THAM KHẢO:\n" + "\n\n".join(
                f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts)
            )

            question_section = f"\n\nCÂU HỎI: {question}\n\nTRẢ LỜI:"

        else:  # English
            system_instruction = (
                "You are an intelligent AI assistant for PTIT (Posts and Telecommunications Institute of Technology). "
                "Your task is to answer questions based on the information provided below.\n\n"
                "Rules:\n"
                "1. Only answer based on the provided information\n"
                "2. If there's insufficient information, clearly state that\n"
                "3. Keep answers concise, accurate, and easy to understand\n\n"
            )

            context_section = "REFERENCE INFORMATION:\n" + "\n\n".join(
                f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts)
            )

            question_section = f"\n\nQUESTION: {question}\n\nANSWER:"

        return system_instruction + context_section + question_section

    def generate_with_citations(self, question: str, contexts: List[str], language: str = "vi") -> str:
        """
        Generate answer with inline citations [1], [2], etc.

        Args:
            question: User's question
            contexts: Retrieved context chunks
            language: Language for answer

        Returns:
            Generated answer with citation markers
        """
        prompt = self._build_prompt_with_citations(question, contexts, language)
        answer = self.client.complete(prompt, max_tokens=self.max_tokens, temperature=0.7)
        return answer

    def _build_prompt_with_citations(self, question: str, contexts: List[str], language: str) -> str:
        """
        Build prompt that encourages inline citations

        Args:
            question: User's question
            contexts: Retrieved context chunks
            language: Language for prompt

        Returns:
            Formatted prompt with citation instructions
        """
        if language == "vi":
            citation_instruction = (
                "Khi trả lời, hãy trích dẫn nguồn bằng cách thêm [1], [2], v.v. "
                "sau các thông tin bạn sử dụng từ tài liệu tham khảo.\n\n"
            )
        else:
            citation_instruction = (
                "When answering, cite sources by adding [1], [2], etc. "
                "after information you use from the reference documents.\n\n"
            )

        base_prompt = self._build_prompt(question, contexts, language)
        return base_prompt.replace("TRẢ LỜI:", citation_instruction + "TRẢ LỜI:") if language == "vi" else \
               base_prompt.replace("ANSWER:", citation_instruction + "ANSWER:")

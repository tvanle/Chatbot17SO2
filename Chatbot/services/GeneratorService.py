"""
GeneratorService - Generates answers using LLM with retrieved context
"""
from typing import List
from Chatbot.services.ModelClient import ModelClient


class GeneratorService:
    """
    Service for generating answers using LLM
    Combines user question with retrieved context chunks
    """

    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        max_tokens: int = 512,
        backend: str = "openai"
    ):
        """
        Initialize generator service

        Args:
            model_name: LLM model identifier
            max_tokens: Maximum tokens for generation
            backend: LLM backend ("openai", "anthropic", "local")
        """
        self.client = ModelClient(model_name=model_name, backend=backend)
        self.max_tokens = max_tokens

    def generate(self, question: str, contexts: List[str], language: str = "vi") -> str:
        """
        Generate answer to question using context chunks

        Args:
            question: User's question
            contexts: Retrieved context chunks (relevant text passages)
            language: Language for answer ("vi" or "en")

        Returns:
            Generated answer
        """
        # Build prompt with context and question
        prompt = self._build_prompt(question, contexts, language)

        # Generate answer using LLM
        answer = self.client.complete(prompt, max_tokens=self.max_tokens, temperature=0.7)

        return answer

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
                "Bạn là trợ lý AI thông minh của Học viện Công nghệ Bưu chính Viễn thông (PTIT). "
                "Nhiệm vụ của bạn là trả lời câu hỏi dựa trên các thông tin được cung cấp bên dưới.\n\n"
                "Quy tắc:\n"
                "1. Chỉ trả lời dựa trên thông tin được cung cấp\n"
                "2. Nếu không có đủ thông tin, hãy nói rõ điều đó\n"
                "3. Trả lời ngắn gọn, chính xác, dễ hiểu\n"
                "4. Sử dụng tiếng Việt có dấu chuẩn\n\n"
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
        return base_prompt.replace("TRẢLỜI:", citation_instruction + "TRẢ LỜI:") if language == "vi" else \
               base_prompt.replace("ANSWER:", citation_instruction + "ANSWER:")

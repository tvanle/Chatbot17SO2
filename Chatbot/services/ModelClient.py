"""
ModelClient - Client for LLM inference
Supports multiple backends: OpenAI, Claude, Local models
"""
from typing import Optional, Dict
import os


class ModelClient:
    """
    Client for Large Language Model completions
    Supports OpenAI GPT, Anthropic Claude, or local models
    """

    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        backend: str = "openai"  # "openai", "anthropic", "local"
    ):
        """
        Initialize model client

        Args:
            model_name: Model identifier (e.g., "gpt-3.5-turbo", "claude-3-sonnet")
            api_key: API key (if using cloud provider)
            backend: Which LLM backend to use
        """
        self.model_name = model_name
        self.backend = backend
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate LLM client"""
        try:
            if self.backend == "openai":
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                print(f"Initialized OpenAI client with model: {self.model_name}")
            elif self.backend == "anthropic":
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
                print(f"Initialized Anthropic client with model: {self.model_name}")
            elif self.backend == "local":
                # Placeholder for local model (e.g., using transformers)
                print(f"Local model backend: {self.model_name}")
                self.client = None
            else:
                print(f"Unknown backend: {self.backend}")
                self.client = None
        except ImportError as e:
            print(f"Failed to import LLM library: {e}")
            self.client = None
        except Exception as e:
            print(f"Error initializing LLM client: {e}")
            self.client = None

    def complete(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """
        Generate completion from prompt

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)

        Returns:
            Generated text completion
        """
        if self.client is None:
            return self._mock_completion(prompt)

        try:
            if self.backend == "openai":
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return response.choices[0].message.content

            elif self.backend == "anthropic":
                response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

            elif self.backend == "local":
                # Placeholder for local model inference
                return self._mock_completion(prompt)

        except Exception as e:
            print(f"Error generating completion: {e}")
            return self._mock_completion(prompt)

    def _mock_completion(self, prompt: str) -> str:
        """
        Mock completion for testing (when no real LLM available)
        Extracts and returns the retrieved contexts from the prompt
        """
        # Log full prompt to console
        print("\n" + "="*80)
        print("🔍 RAG RETRIEVAL - No API Key Configured")
        print("="*80)

        # Extract contexts from prompt
        contexts = []
        if "THÔNG TIN THAM KHẢO:" in prompt:
            # Extract Vietnamese context section
            parts = prompt.split("THÔNG TIN THAM KHẢO:")
            if len(parts) > 1:
                context_section = parts[1].split("CÂU HỎI:")[0].strip()
                contexts = [ctx.strip() for ctx in context_section.split("\n\n") if ctx.strip()]
        elif "REFERENCE INFORMATION:" in prompt:
            # Extract English context section
            parts = prompt.split("REFERENCE INFORMATION:")
            if len(parts) > 1:
                context_section = parts[1].split("QUESTION:")[0].strip()
                contexts = [ctx.strip() for ctx in context_section.split("\n\n") if ctx.strip()]

        # Log extracted contexts
        if contexts:
            print("📚 Nội dung tìm được từ Vector Database:\n")
            for i, ctx in enumerate(contexts, 1):
                print(f"[{i}] {ctx}\n")
        else:
            print("⚠️  Không tìm thấy context trong prompt")

        print("="*80)
        print("💡 Để sinh câu trả lời tự động, vui lòng cấu hình:")
        print("   - OPENAI_API_KEY (GPT-3.5/GPT-4)")
        print("   - hoặc ANTHROPIC_API_KEY (Claude)")
        print("="*80 + "\n")

        # Return message to user
        result = "⚠️ **Chưa cấu hình API Key LLM**\n\n"
        result += "Hệ thống đã tìm thấy thông tin liên quan từ cơ sở dữ liệu, "
        result += "nhưng cần API key để sinh câu trả lời tự động.\n\n"

        if contexts:
            result += "📚 **Thông tin tìm được:**\n\n"
            for ctx in contexts:
                result += f"{ctx}\n\n"
            result += "\n---\n\n"

        result += "💡 **Hướng dẫn cấu hình:**\n"
        result += "- Thêm OPENAI_API_KEY vào file .env\n"
        result += "- Hoặc thêm ANTHROPIC_API_KEY vào file .env\n"

        return result

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text (approximate)

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Simple approximation: 1 token ≈ 4 characters
        return len(text) // 4

    def get_context_window(self) -> int:
        """
        Get model's context window size

        Returns:
            Maximum context length in tokens
        """
        context_windows = {
            "gpt-3.5-turbo": 4096,
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "claude-3-sonnet": 200000,
            "claude-3-opus": 200000,
        }
        return context_windows.get(self.model_name, 4096)

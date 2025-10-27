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
        """
        return (
            "Đây là câu trả lời mẫu từ hệ thống RAG chatbot. "
            "Để sử dụng LLM thực, vui lòng cấu hình API key và model. "
            f"Prompt length: {len(prompt)} chars."
        )

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

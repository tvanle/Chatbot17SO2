"""
ModelClient - Client for LLM inference
Supports multiple backends: OpenAI, Claude, Local models
Enhanced with conversation history support
"""
from typing import Optional, Dict, List
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

    def complete(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate completion from prompt with optional conversation history

        Args:
            prompt: Current user prompt/question
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            messages: Optional conversation history in format:
                     [{"role": "system|user|assistant", "content": "..."}]
                     If provided, ignores single prompt parameter

        Returns:
            Generated text completion
        """
        if self.client is None:
            return self._mock_completion(prompt)

        try:
            # Build messages list
            if messages is None:
                # Single-turn: just the user prompt
                messages = [{"role": "user", "content": prompt}]

            if self.backend == "openai":
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return response.choices[0].message.content

            elif self.backend == "anthropic":
                # Anthropic requires separating system message
                system_msg = None
                conversation_msgs = []

                for msg in messages:
                    if msg["role"] == "system":
                        system_msg = msg["content"]
                    else:
                        conversation_msgs.append(msg)

                kwargs = {
                    "model": self.model_name,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": conversation_msgs
                }
                if system_msg:
                    kwargs["system"] = system_msg

                response = self.client.messages.create(**kwargs)
                return response.content[0].text

            elif self.backend == "local":
                # Placeholder for local model inference
                return self._mock_completion(prompt)

        except Exception as e:
            print(f"Error generating completion: {e}")
            return self._mock_completion(prompt)

    def _safe_print(self, text: str):
        """Print with encoding error handling for Windows console"""
        try:
            print(text)
        except UnicodeEncodeError:
            # Fallback to ASCII-only if console doesn't support Vietnamese
            print(text.encode('ascii', 'ignore').decode('ascii'))

    def _mock_completion(self, prompt: str) -> str:
        """
        Mock completion for testing (when no real LLM available)
        Extracts and returns the retrieved contexts from the prompt
        """
        # Log full prompt to console
        self._safe_print("\n" + "="*80)
        self._safe_print("RAG RETRIEVAL - No API Key Configured")
        self._safe_print("="*80)

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
            self._safe_print("Noi dung tim duoc tu Vector Database:\n")
            for i, ctx in enumerate(contexts, 1):
                self._safe_print(f"[{i}] {ctx}\n")
        else:
            self._safe_print("Khong tim thay context trong prompt")

        self._safe_print("="*80)
        self._safe_print("De sinh cau tra loi tu dong, vui long cau hinh:")
        self._safe_print("   - OPENAI_API_KEY (GPT-3.5/GPT-4)")
        self._safe_print("   - hoac ANTHROPIC_API_KEY (Claude)")
        self._safe_print("="*80 + "\n")

        # Return message to user
        result = "**Chua cau hinh API Key LLM**\n\n"
        result += "He thong da tim thay thong tin lien quan tu co so du lieu, "
        result += "nhung can API key de sinh cau tra loi tu dong.\n\n"

        if contexts:
            result += "**Thong tin tim duoc:**\n\n"
            for ctx in contexts:
                result += f"{ctx}\n\n"
            result += "\n---\n\n"

        result += "**Huong dan cau hinh:**\n"
        result += "- Them OPENAI_API_KEY vao file .env\n"
        result += "- Hoac them ANTHROPIC_API_KEY vao file .env\n"

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

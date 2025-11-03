"""
ModelProviderService - Fetch available models from API providers
Automatically detects which API keys are configured and returns available models
"""
import os
from typing import List, Dict, Optional


class ModelProviderService:
    """
    Service to fetch available models from configured API providers
    """

    @staticmethod
    def get_available_models() -> List[Dict[str, str]]:
        """
        Get list of available models based on configured API keys

        Returns:
            List of model dictionaries with name, description, api_identifier
        """
        models = []

        # Check OpenAI API key
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            models.extend(ModelProviderService._get_openai_models())

        # Check Anthropic API key
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            models.extend(ModelProviderService._get_anthropic_models())

        # Check Google AI key (Gemini)
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            models.extend(ModelProviderService._get_google_models())

        # If no API keys configured, return mock models
        if not models:
            models = ModelProviderService._get_mock_models()

        return models

    @staticmethod
    def _get_openai_models() -> List[Dict[str, str]]:
        """Get available OpenAI models"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Fetch real models from OpenAI API
            response = client.models.list()
            available_model_ids = [model.id for model in response.data]

            # Define our supported models with descriptions
            supported_models = [
                {
                    "id": "gpt-4o",
                    "name": "ChatGPT 4o",
                    "description": "Model mạnh nhất của OpenAI, phù hợp cho các tác vụ phức tạp"
                },
                {
                    "id": "gpt-4o-mini",
                    "name": "ChatGPT 4o mini",
                    "description": "Phiên bản nhẹ hơn, nhanh và tiết kiệm chi phí"
                },
                {
                    "id": "gpt-4-turbo",
                    "name": "ChatGPT 4 Turbo",
                    "description": "GPT-4 với context window lớn hơn (128K tokens)"
                }
            ]

            # Filter only available models
            models = []
            for model in supported_models:
                if model["id"] in available_model_ids:
                    models.append({
                        "name": model["name"],
                        "description": model["description"],
                        "api_identifier": model["id"]
                    })

            print(f"Found {len(models)} OpenAI models")
            return models

        except Exception as e:
            print(f"Error fetching OpenAI models: {e}")
            # Fallback to hardcoded list
            return [
                {
                    "name": "ChatGPT 4o",
                    "description": "Model mạnh nhất của OpenAI, phù hợp cho các tác vụ phức tạp",
                    "api_identifier": "gpt-4o"
                },
                {
                    "name": "ChatGPT 4o mini",
                    "description": "Phiên bản nhẹ hơn, nhanh và tiết kiệm chi phí",
                    "api_identifier": "gpt-4o-mini"
                },
                {
                    "name": "ChatGPT 3.5 Turbo",
                    "description": "Nhanh và hiệu quả, phù hợp cho hầu hết các tác vụ",
                    "api_identifier": "gpt-3.5-turbo"
                }
            ]

    @staticmethod
    def _get_anthropic_models() -> List[Dict[str, str]]:
        """Get available Anthropic models"""
        try:
            # Anthropic doesn't have a models.list() endpoint
            # Return supported models based on documentation
            return [
                {
                    "name": "Claude 3.5 Sonnet",
                    "description": "Model thông minh của Anthropic, xuất sắc trong lập luận phức tạp",
                    "api_identifier": "claude-3-5-sonnet-20241022"
                },
                {
                    "name": "Claude 3 Opus",
                    "description": "Model mạnh nhất của Anthropic cho các tác vụ phức tạp nhất",
                    "api_identifier": "claude-3-opus-20240229"
                },
                {
                    "name": "Claude 3 Haiku",
                    "description": "Model nhanh và nhẹ nhất của Anthropic",
                    "api_identifier": "claude-3-haiku-20240307"
                }
            ]
        except Exception as e:
            print(f"Error fetching Anthropic models: {e}")
            return []

    @staticmethod
    def _get_google_models() -> List[Dict[str, str]]:
        """Get available Google AI models (Gemini)"""
        try:
            return [
                {
                    "name": "Gemini 2.0 Flash",
                    "description": "Model nhanh của Google, tốt cho xử lý đa phương tiện",
                    "api_identifier": "gemini-2.0-flash-exp"
                },
                {
                    "name": "Gemini 1.5 Pro",
                    "description": "Model mạnh của Google với context window cực lớn (2M tokens)",
                    "api_identifier": "gemini-1.5-pro"
                }
            ]
        except Exception as e:
            print(f"Error fetching Google models: {e}")
            return []

    @staticmethod
    def _get_mock_models() -> List[Dict[str, str]]:
        """
        Return mock models when no API keys configured
        These will use the mock completion in ModelClient
        """
        return [
            {
                "name": "Mock Model (No API Key)",
                "description": "Chế độ demo - trả về thông tin tìm được từ vector DB",
                "api_identifier": "mock-model"
            }
        ]

    @staticmethod
    def validate_model(model_id: str) -> bool:
        """
        Validate if a model is available

        Args:
            model_id: Model API identifier

        Returns:
            True if model is available, False otherwise
        """
        available_models = ModelProviderService.get_available_models()
        return any(m["api_identifier"] == model_id for m in available_models)

    @staticmethod
    def get_model_backend(model_id: str) -> Optional[str]:
        """
        Determine which backend to use for a given model

        Args:
            model_id: Model API identifier

        Returns:
            "openai", "anthropic", "google", or None
        """
        if model_id.startswith("gpt-"):
            return "openai"
        elif model_id.startswith("claude-"):
            return "anthropic"
        elif model_id.startswith("gemini-"):
            return "google"
        else:
            return "openai"  # Default fallback

"""
OpenAI image generation and vision provider.
Uses GPT-4.1-mini with tools for generation and vision capabilities.
"""

import base64
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.core.interfaces import IImageProvider

logger = logging.getLogger(__name__)


class OpenAIImageProvider(IImageProvider):
    """
    OpenAI image generation and vision provider.
    - Generation: GPT-4.1-mini with image_generation tool
    - Vision: GPT-4.1-mini with image input
    """
    
    def __init__(self, api_key: str):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
        """
        self.client = OpenAI(api_key=api_key)
        self.generation_model = "gpt-4.1-mini"
        self.vision_model = "gpt-4.1-mini"
        logger.info("OpenAI Image Provider initialized")
    
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: str = "natural",
    ) -> bytes:
        """
        Generate image using GPT-4.1-mini with image_generation tool.
        
        Args:
            prompt: Text description of desired image
            size: Image size ("1024x1024", "1792x1024", "1024x1792")
            style: Image style ("natural", "vivid")
            
        Returns:
            Image bytes in PNG format
            
        Raises:
            RuntimeError: If generation fails
        """
        try:
            logger.info(f"Generating image: '{prompt[:80]}...'")
            
            # Call OpenAI with image generation tool
            response = self.client.responses.create(
                model=self.generation_model,
                input=prompt,
                tools=[{"type": "image_generation"}],
                metadata={
                    "style": style,
                    "size": size,
                }
            )
            
            # Extract image data from response
            image_data_list = [
                output.result
                for output in response.output
                if output.type == "image_generation_call"
            ]
            
            if not image_data_list:
                raise ValueError("No image generated in response")
            
            # Decode base64 to bytes
            image_base64 = image_data_list[0]
            image_bytes = base64.b64decode(image_base64)
            
            logger.info(f"✓ Image generated successfully ({len(image_bytes)} bytes)")
            
            return image_bytes
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise RuntimeError(f"Failed to generate image: {str(e)}")
    
    async def analyze_image(
        self,
        image_url: str,
        question: str = "What's in this image?",
        detail: str = "auto",
    ) -> Dict[str, Any]:
        """
        Analyze image using GPT-4 Vision.
        
        Args:
            image_url: Public URL or base64 data URL of image
            question: Question to ask about the image
            detail: Level of detail ("auto", "low", "high")
            
        Returns:
            Dictionary with:
                - description: AI description of image
                - labels: List of detected objects/concepts
                - model: Model used for analysis
                - detail_level: Detail level used
                
        Raises:
            RuntimeError: If analysis fails
        """
        try:
            logger.info(f"Analyzing image: {image_url[:80]}...")
            
            # Call OpenAI Vision API
            response = self.client.responses.create(
                model=self.vision_model,
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": question},
                        {
                            "type": "input_image",
                            "image_url": image_url,
                            "detail": detail,
                        },
                    ],
                }],
            )
            
            # Extract description from response
            description = response.output_text.strip()
            
            # Extract labels from description (simple keyword extraction)
            labels = self._extract_labels_from_description(description)
            
            result = {
                "description": description,
                "labels": labels,
                "model": self.vision_model,
                "detail_level": detail,
            }
            
            logger.info(f"✓ Image analyzed: {len(labels)} labels found")
            logger.debug(f"Description: {description[:100]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            raise RuntimeError(f"Failed to analyze image: {str(e)}")
    
    async def extract_text_ocr(self, image_url: str) -> Optional[str]:
        """
        Extract text from image using Vision API (OCR).
        
        Args:
            image_url: URL to image
            
        Returns:
            Extracted text or None if no text found
        """
        try:
            logger.info(f"Extracting text from image: {image_url[:80]}...")
            
            # Use vision API with specific OCR prompt
            result = await self.analyze_image(
                image_url=image_url,
                question=(
                    "Extract all visible text from this image. "
                    "Return ONLY the text content, nothing else. "
                    "If there's no text, respond with 'NO_TEXT'."
                ),
                detail="high",  # Use high detail for better OCR
            )
            
            extracted_text = result.get("description", "")
            
            # Check if meaningful text was found
            if not extracted_text or extracted_text == "NO_TEXT" or len(extracted_text) < 3:
                logger.info("No text found in image")
                return None
            
            logger.info(f"✓ Extracted {len(extracted_text)} characters of text")
            
            return extracted_text
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return None
    
    def _extract_labels_from_description(self, description: str) -> List[str]:
        """
        Extract key labels/tags from AI description.
        Simple implementation using common patterns.
        
        Args:
            description: AI-generated description
            
        Returns:
            List of extracted labels
        """
        # This is a simple implementation
        # Can be improved with NLP libraries like spaCy
        
        labels = []
        
        # Common object/scene keywords to look for
        keywords = [
            # People & animals
            "person", "people", "man", "woman", "child", "baby",
            "dog", "cat", "bird", "animal", "pet",
            
            # Places
            "beach", "mountain", "forest", "city", "building",
            "house", "room", "office", "street", "park",
            
            # Nature
            "sky", "cloud", "sun", "sunset", "sunrise",
            "tree", "flower", "water", "ocean", "river",
            
            # Objects
            "car", "computer", "phone", "book", "food",
            "table", "chair", "door", "window",
            
            # Activities
            "walking", "running", "sitting", "standing",
            "eating", "working", "playing",
        ]
        
        description_lower = description.lower()
        
        for keyword in keywords:
            if keyword in description_lower:
                labels.append(keyword)
        
        # Remove duplicates and limit to 10 labels
        labels = list(set(labels))[:10]
        
        return labels


import os
import json
import logging
from typing import Optional, Dict, Any
from google import genai
from google.genai import types
from models import CONTENT_MODE_TEMPERATURES, ContentMode

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_key)

    def generate_content(self, prompt: str, content_mode: Optional[str] = None, 
                        brand_voice_context: Optional[str] = None,
                        trauma_informed_context: Optional[str] = None) -> str:
        """Generate content using Gemini with trauma-informed and brand voice context"""
        try:
            # Get temperature based on content mode
            temperature = CONTENT_MODE_TEMPERATURES.get(content_mode or 'general', 0.7)
            
            # Build system instruction
            system_instruction = self._build_system_instruction(
                content_mode, brand_voice_context, trauma_informed_context
            )
            
            # Build final prompt with context
            final_prompt = self._build_prompt_with_context(
                prompt, content_mode, brand_voice_context, trauma_informed_context
            )
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[types.Content(role="user", parts=[types.Part(text=final_prompt)])],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=temperature,
                    max_output_tokens=4096
                )
            )
            
            if response.text:
                return response.text
            else:
                return "I apologize, but I wasn't able to generate a response. Please try again."
                
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            return f"I'm sorry, but I encountered an error while processing your request. Please try again."

    def _build_system_instruction(self, content_mode: Optional[str], 
                                 brand_voice_context: Optional[str],
                                 trauma_informed_context: Optional[str]) -> str:
        """Build the system instruction for Gemini"""
        
        base_instruction = """You are GoldenDoodleLM, an empathetic, encouraging, and supportive AI assistant designed specifically for trauma-informed nonprofit organizations. Your primary mission is to help communications and marketing teams create high-quality, on-brand, trauma-informed content.

Core Principles:
1. Always use trauma-informed communication principles
2. Be empathetic, encouraging, and supportive in tone
3. Prioritize safety, trustworthiness, and empowerment in all content
4. Use person-first language and avoid stigmatizing terms
5. Focus on strengths and resilience rather than deficits
6. Provide hope and actionable information
7. Be culturally responsive and inclusive
8. Maintain professional boundaries while being warm and approachable"""

        if content_mode:
            mode_instructions = {
                ContentMode.EMAIL: "Focus on professional, empathetic email communication that builds trust and connection.",
                ContentMode.ARTICLE: "Create informative, well-structured content that educates while maintaining trauma-informed principles.",
                ContentMode.SOCIAL_MEDIA: "Generate engaging, accessible social media content that's appropriate for trauma survivors.",
                ContentMode.REWRITE: "Transform existing content to be more trauma-informed while preserving the original message.",
                ContentMode.SUMMARIZE: "Provide clear, concise summaries that maintain sensitivity to trauma-related topics.",
                ContentMode.BRAINSTORM: "Generate creative, innovative ideas while ensuring all suggestions are trauma-informed.",
                ContentMode.ANALYZE: "Provide thoughtful analysis that considers trauma-informed perspectives and implications."
            }
            
            if content_mode in mode_instructions:
                base_instruction += f"\n\nCurrent Mode: {mode_instructions[content_mode]}"

        if trauma_informed_context:
            base_instruction += f"\n\nTrauma-Informed Context:\n{trauma_informed_context}"

        if brand_voice_context:
            base_instruction += f"\n\nBrand Voice Guidelines:\n{brand_voice_context}"

        return base_instruction

    def _build_prompt_with_context(self, user_prompt: str, content_mode: Optional[str],
                                  brand_voice_context: Optional[str],
                                  trauma_informed_context: Optional[str]) -> str:
        """Build the final prompt with all context"""
        
        context_parts = []
        
        if content_mode:
            from models import CONTENT_MODE_CONFIG
            mode_config = CONTENT_MODE_CONFIG.get(content_mode, {})
            mode_name = mode_config.get('name', content_mode)
            context_parts.append(f"Content Mode: {mode_name}")

        prompt_parts = context_parts + [user_prompt]
        return "\n\n".join(prompt_parts)

# Global service instance
gemini_service = GeminiService()

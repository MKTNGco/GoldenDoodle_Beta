import os
import json
import logging
from typing import Optional, Dict, Any
import google.genai as genai
from google.genai import types
from models import CONTENT_MODE_TEMPERATURES, ContentMode, CONTENT_MODE_CONFIG
from rag_service import rag_service

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        logger.info(f"Initializing Gemini service with API key: {api_key[:10]}...")
        self.client = genai.Client(api_key=api_key)
        # Model name to use for generation
        self.model_name = 'gemini-2.5-flash'
        
        # Test the connection
        try:
            logger.info("Testing Gemini API connection...")
            test_response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[types.Content(role="user", parts=[types.Part(text="Test")])],
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=100
                )
            )
            logger.info(f"✓ Gemini API connection successful! Test response: {test_response.text[:50] if test_response.text else 'No text'}")
        except Exception as e:
            logger.error(f"❌ Gemini API connection failed during initialization: {e}")
            raise


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

    def generate_content_with_history(self, prompt: str, conversation_history: list = None,
                                    content_mode: str = None, brand_voice_context: str = None, 
                                    trauma_informed_context: str = None) -> str:
        """Generate content using Gemini with conversation history for context"""
        try:
            logger.info(f"Generating content with history. Prompt length: {len(prompt)}")
            logger.info(f"History length: {len(conversation_history) if conversation_history else 0}")
            logger.info(f"Content mode: {content_mode}")
            
            # Build conversation history string
            history_context = ""
            if conversation_history:
                history_context = "\n\n=== CONVERSATION HISTORY ===\n"
                for msg in conversation_history:
                    role = msg.get('role', '').upper()
                    content = msg.get('content', '')
                    if role == 'USER':
                        history_context += f"USER: {content}\n"
                    elif role == 'ASSISTANT':
                        history_context += f"ASSISTANT: {content}\n"
                history_context += "=== END CONVERSATION HISTORY ===\n\n"

            # Build the full prompt with context and history
            full_prompt = self._build_prompt_with_history(prompt, history_context, content_mode, brand_voice_context, trauma_informed_context)
            logger.info(f"Full prompt length: {len(full_prompt)}")

            # Get temperature based on content mode (same as the working generate_content method)
            temperature = CONTENT_MODE_TEMPERATURES.get(content_mode or 'general', 0.7)
            
            # Build system instruction (same approach as working method)
            system_instruction = self._build_system_instruction(
                content_mode, brand_voice_context, trauma_informed_context
            )
            
            # Generate content with detailed logging (using same structure as working method)
            logger.info("Making API call to Gemini...")
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[types.Content(role="user", parts=[types.Part(text=full_prompt)])],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=temperature,
                    max_output_tokens=4096
                )
            )
            
            logger.info(f"API call completed. Response type: {type(response)}")
            logger.info(f"Response object: {response}")

            logger.info(f"Raw response received: {response}")
            logger.info(f"Response type: {type(response)}")
            
            if response:
                # First try the direct .text attribute
                if hasattr(response, 'text') and response.text:
                    logger.info(f"Success! Found response.text with length: {len(response.text)}")
                    return response.text.strip()
                
                # If that fails, log the full response structure for debugging
                logger.warning(f"Response structure debugging:")
                logger.warning(f"  - hasattr(response, 'text'): {hasattr(response, 'text')}")
                logger.warning(f"  - response.text value: {getattr(response, 'text', 'NOT_FOUND')}")
                logger.warning(f"  - hasattr(response, 'candidates'): {hasattr(response, 'candidates')}")
                
                if hasattr(response, 'candidates'):
                    logger.warning(f"  - response.candidates: {response.candidates}")
                    logger.warning(f"  - response.candidates type: {type(response.candidates)}")
                    
                # Log all available attributes
                logger.warning(f"  - Available attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
                
                # Try to access candidates if available
                if hasattr(response, 'candidates') and response.candidates:
                    logger.info("Trying to extract from candidates...")
                    for i, candidate in enumerate(response.candidates):
                        logger.info(f"  Candidate {i}: {type(candidate)}")
                        if hasattr(candidate, 'content'):
                            logger.info(f"    Has content: {type(candidate.content)}")
                            if hasattr(candidate.content, 'parts'):
                                logger.info(f"    Has parts: {len(candidate.content.parts) if candidate.content.parts else 0}")
                                for j, part in enumerate(candidate.content.parts):
                                    logger.info(f"      Part {j}: {type(part)}")
                                    if hasattr(part, 'text') and part.text:
                                        logger.info(f"Success! Found text in candidate {i}, part {j}")
                                        return part.text.strip()
                
                # If we get here, we couldn't extract text
                logger.error("Failed to extract text from response using all methods")
                return "I apologize, but I wasn't able to generate a response. Please try again."
            else:
                logger.warning("No response received from Gemini API")
                return "I apologize, but I wasn't able to generate a response. Please try again."

        except Exception as e:
            logger.error(f"Exception in generate_content_with_history: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return "I'm experiencing technical difficulties. Please try again in a moment."

    def _build_system_instruction(self, content_mode: Optional[str], 
                                 brand_voice_context: Optional[str],
                                 trauma_informed_context: Optional[str]) -> str:
        """Build the system instruction for Gemini"""

        base_instruction = """You are GoldenDoodleLM, an empathetic, encouraging, and supportive AI assistant designed specifically for trauma-informed nonprofit organizations. Your primary mission is to help communications and marketing teams create high-quality, on-brand, trauma-informed content.

Core Response Philosophy - The Gracious Approach:
Directly fulfill the user's request while naturally modeling trauma-informed language and principles. Do not correct the user's language choices or reframe their queries. Instead, respond with dignity and respect, incorporating empowering language organically within your response.

Your responses should always be:
- Gentle, non-judgmental, and empathetic
- Professional while maintaining warmth
- Focused on the user's actual needs
- Naturally incorporating person-first, strengths-based language
- Emphasizing hope, possibility, and healing

Core Trauma-Informed Principles:
1. Person-First Language: Model language that puts the person before their experience or condition
2. Strengths-Based Approach: Focus on resilience, capabilities, and potential rather than deficits
3. Cultural Sensitivity: Recognize and respect diverse backgrounds and experiences
4. Empowerment and Choice: Provide options and respect individual autonomy
5. Safety and Trust: Create psychologically and physically safe environments
6. Collaboration: Work with rather than for people, recognizing their expertise

Natural Language Modeling:
- Use "person who experienced..." instead of "victim" when creating content
- Choose "lives with" or "experiences" over "suffers from"
- Use "healing" or "working through challenges" instead of "broken" or "damaged"
- Select "experiencing distress" over stigmatizing terms
- Focus on empowerment, resilience, and growth
- Maintain therapeutic relationship through respectful engagement"""

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
        else:
            # Get mode-specific trauma-informed guidance
            specific_guidance = rag_service.get_content_mode_specific_guidance(content_mode or 'general')
            if specific_guidance:
                base_instruction += f"\n\nTrauma-Informed Guidelines:\n{specific_guidance}"

        if brand_voice_context:
            base_instruction += f"\n\nBrand Voice Guidelines:\n{brand_voice_context}"

        return base_instruction

    def _build_prompt_with_context(self, user_prompt: str, content_mode: Optional[str],
                                  brand_voice_context: Optional[str],
                                  trauma_informed_context: Optional[str]) -> str:
        """Build the final prompt with all context"""

        context_parts = []

        if content_mode:
            mode_config = CONTENT_MODE_CONFIG.get(content_mode, {})
            mode_name = mode_config.get('name', content_mode)
            context_parts.append(f"Content Mode: {mode_name}")

        prompt_parts = context_parts + [user_prompt]
        return "\n\n".join(prompt_parts)

    def _build_prompt_with_history(self, user_prompt: str, history_context: str = "", 
                                  content_mode: str = None, brand_voice_context: str = None, 
                                  trauma_informed_context: str = None) -> str:
        """Build a comprehensive prompt with conversation history and all context"""

        # Start with system instructions
        prompt_parts = [
            "You are GoldenDoodleLM, a trauma-informed AI assistant specializing in compassionate, healing-centered communication.",
            "Your responses should always prioritize psychological safety, cultural responsiveness, and strengths-based language.",
            "You maintain conversation context and can reference previous exchanges to provide more helpful and relevant responses.",
            ""
        ]

        # Add conversation history if provided
        if history_context:
            prompt_parts.extend([
                history_context
            ])

        # Add trauma-informed context
        if trauma_informed_context:
            prompt_parts.extend([
                "=== TRAUMA-INFORMED COMMUNICATION GUIDELINES ===",
                trauma_informed_context,
                ""
            ])

        # Add brand voice context if provided
        if brand_voice_context:
            prompt_parts.extend([
                "=== BRAND VOICE GUIDELINES ===",
                brand_voice_context,
                ""
            ])

        # Add content mode specific instructions
        if content_mode and content_mode in CONTENT_MODE_CONFIG:
            mode_config = CONTENT_MODE_CONFIG[content_mode]
            prompt_parts.extend([
                f"=== {mode_config['name'].upper()} MODE ===",
                f"Context: {mode_config['description']}",
                f"Focus: {mode_config['focus']}",
                ""
            ])

        # Add the user's current request
        prompt_parts.extend([
            "=== CURRENT USER REQUEST ===",
            user_prompt,
            "",
            "Please respond to the current request, taking into account the conversation history and following all the guidelines above. Ensure your communication is trauma-informed, culturally responsive, and aligned with any provided brand voice."
        ])

        return "\n".join(prompt_parts)


# Global service instance
gemini_service = GeminiService()
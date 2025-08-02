
import os
import logging
from typing import Optional, List, Dict, Any
from trauma_informed_protocols import (
    TRAUMA_INFORMED_KNOWLEDGE, 
    PROTOCOL_INDEX, 
    search_protocols, 
    get_protocol_by_category,
    validate_trauma_informed_content,
    get_language_replacement
)

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        # Load the comprehensive trauma-informed knowledge base
        self.trauma_informed_knowledge = TRAUMA_INFORMED_KNOWLEDGE
        self.protocol_index = PROTOCOL_INDEX

    def get_trauma_informed_context(self, content_mode: Optional[str] = None) -> str:
        """Get trauma-informed communication context based on content mode"""
        
        # Default general principles
        context = self.trauma_informed_knowledge['general_principles']
        
        # Add mode-specific guidelines
        if content_mode:
            mode_mapping = {
                'email': 'email_communication',
                'article': 'written_communication',
                'social_media': 'social_media_guidelines',
                'rewrite': 'rewriting_guidelines',
                'crisis': 'crisis_communication'
            }
            
            specific_guidelines = mode_mapping.get(content_mode.lower())
            if specific_guidelines and specific_guidelines in self.trauma_informed_knowledge:
                context += f"\n\nSpecific Guidelines for {content_mode}:\n"
                context += self.trauma_informed_knowledge[specific_guidelines]
        
        return context

    def get_brand_voice_context(self, brand_voice_markdown: Optional[str]) -> Optional[str]:
        """Get brand voice context from markdown content"""
        if not brand_voice_markdown:
            return None
        
        # In a full implementation, this would use LlamaIndex to process
        # the markdown and create embeddings for retrieval
        # For now, we'll return the markdown directly as context
        return brand_voice_markdown

    def search_knowledge_base(self, query: str, knowledge_type: str = "trauma_informed") -> List[str]:
        """Search the knowledge base for relevant information"""
        
        if knowledge_type == "trauma_informed":
            # Use the new protocol search system
            matches = search_protocols(query)
            
            if matches:
                relevant_sections = []
                for protocol_id, match_info in matches.items():
                    relevant_sections.append(match_info['description'])
                    # Add specific content excerpts
                    for content in match_info['content']:
                        if content:
                            # Extract first few lines as preview
                            lines = content.split('\n')[:3]
                            preview = '\n'.join(lines).strip()
                            if preview:
                                relevant_sections.append(preview)
                
                return relevant_sections[:5]  # Limit to top 5 most relevant
            
            # Fallback to keyword-based search
            return self._keyword_search(query)
        
        return []

    def _keyword_search(self, query: str) -> List[str]:
        """Fallback keyword-based search for relevant trauma-informed guidance"""
        query_lower = query.lower()
        relevant_sections = []
        
        # Search based on common trauma-informed topics
        if any(word in query_lower for word in ["language", "words", "terminology", "person-first"]):
            relevant_sections.append("Use person-first, strengths-based language that empowers and includes.")
            relevant_sections.append("Avoid stigmatizing terms like 'crazy,' 'broken,' or 'damaged.'")
        
        if any(word in query_lower for word in ["safety", "safe", "trust", "environment"]):
            relevant_sections.append("Prioritize physical and psychological safety in all communications.")
            relevant_sections.append("Create predictable, consistent communication patterns that build trust.")
        
        if any(word in query_lower for word in ["tone", "voice", "approach", "style"]):
            relevant_sections.append("Maintain a warm, empathetic tone that is professional but not overwhelming.")
            relevant_sections.append("Focus on hope, possibility, and empowerment in your communication style.")
        
        if any(word in query_lower for word in ["email", "subject", "professional"]):
            relevant_sections.append("Use clear, specific subject lines and warm professional greetings.")
            relevant_sections.append("Provide context and choices while avoiding aggressive language.")
        
        if any(word in query_lower for word in ["social", "media", "post", "engagement"]):
            relevant_sections.append("Use content warnings for sensitive topics and focus on empowerment.")
            relevant_sections.append("Respond with empathy and direct people to appropriate resources.")
        
        if any(word in query_lower for word in ["crisis", "emergency", "immediate", "urgent"]):
            relevant_sections.append("Use calm, clear language and prioritize immediate safety.")
            relevant_sections.append("Provide concrete next steps and connect to appropriate resources.")
        
        if any(word in query_lower for word in ["rewrite", "revise", "improve", "edit"]):
            relevant_sections.append("Identify stigmatizing language and replace with respectful alternatives.")
            relevant_sections.append("Shift from deficit-based to strengths-based framing.")
        
        return relevant_sections or ["Focus on trauma-informed principles of safety, trustworthiness, and empowerment."]

    def get_protocol_guidance(self, protocol_type: str) -> str:
        """Get specific protocol guidance by type"""
        return get_protocol_by_category(protocol_type)

    def validate_content(self, content: str) -> Dict[str, Any]:
        """Validate content against trauma-informed standards"""
        return validate_trauma_informed_content(content)

    def suggest_language_improvements(self, text: str) -> List[Dict[str, str]]:
        """Suggest language improvements for trauma-informed communication"""
        suggestions = []
        
        # Check for common terms that need replacement
        words = text.lower().split()
        for word in words:
            replacements = get_language_replacement(word)
            if replacements:
                suggestions.append({
                    'original': word,
                    'suggestions': replacements,
                    'reason': 'Consider more trauma-informed language'
                })
        
        return suggestions

    def get_content_mode_specific_guidance(self, mode: str) -> str:
        """Get specific guidance for different content modes"""
        mode_mapping = {
            'email': 'email_communication',
            'article': 'written_communication', 
            'social_media': 'social_media_guidelines',
            'rewrite': 'rewriting_guidelines',
            'crisis': 'crisis_communication',
            'general': 'general_principles'
        }
        
        protocol_type = mode_mapping.get(mode.lower(), 'general_principles')
        return self.get_protocol_guidance(protocol_type)

# Global service instance
rag_service = RAGService()

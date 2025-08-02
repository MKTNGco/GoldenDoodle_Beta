import os
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        # In a full implementation, this would use LlamaIndex
        # For now, we'll provide hardcoded trauma-informed context
        self.trauma_informed_knowledge = self._load_trauma_informed_knowledge()

    def _load_trauma_informed_knowledge(self) -> str:
        """Load trauma-informed communication principles"""
        return """
# Trauma-Informed Communication Principles

## Core Principles
1. **Safety**: Physical and psychological safety for individuals and families
2. **Trustworthiness and Transparency**: Building and maintaining trust through clear communication
3. **Peer Support**: Mutual self-help and shared experiences
4. **Collaboration and Mutuality**: Healing and recovery through meaningful sharing of power
5. **Empowerment and Choice**: Prioritizing empowerment and choice-making
6. **Cultural, Historical, and Gender Issues**: Moving past stereotypes and biases

## Communication Guidelines

### Language to Use:
- Person-first language ("person with a substance use disorder" not "addict")
- Strengths-based language that emphasizes resilience
- Empowering language that suggests agency and choice
- Inclusive language that respects diversity

### Language to Avoid:
- Stigmatizing terms that label or blame
- Medical jargon without explanation
- Assumptions about people's experiences
- Language that minimizes or dismisses feelings

### Content Structure:
- Start with validation and acknowledgment
- Provide clear, actionable information
- Include multiple options and resources
- End with hope and empowerment
- Use bullet points and clear headings for accessibility

### Tone Guidelines:
- Warm and approachable, but professional
- Empathetic without being patronizing
- Confident but not overwhelming
- Respectful of boundaries and autonomy
        """

    def get_trauma_informed_context(self) -> str:
        """Get trauma-informed communication context"""
        return self.trauma_informed_knowledge

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
        # In a full implementation, this would use vector similarity search
        # For now, we'll return relevant sections based on keywords
        
        if knowledge_type == "trauma_informed":
            # Simple keyword matching for demo purposes
            relevant_sections = []
            knowledge = self.trauma_informed_knowledge.lower()
            query_lower = query.lower()
            
            if any(word in query_lower for word in ["language", "words", "terminology"]):
                relevant_sections.append("Use person-first, strengths-based language that empowers and includes.")
            
            if any(word in query_lower for word in ["safety", "safe", "trust"]):
                relevant_sections.append("Prioritize physical and psychological safety in all communications.")
            
            if any(word in query_lower for word in ["tone", "voice", "approach"]):
                relevant_sections.append("Maintain a warm, empathetic tone that is professional but not overwhelming.")
            
            return relevant_sections or ["Focus on trauma-informed principles of safety, trustworthiness, and empowerment."]
        
        return []

# Global service instance
rag_service = RAGService()

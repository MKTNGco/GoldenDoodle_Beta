
TRAUMA_INFORMED_KNOWLEDGE = {
    'general_principles': '''
    Trauma-Informed Communication Core Principles:

    1. Person-First Language: Always put the person before their experience or condition. Say "person who experienced trauma" rather than "trauma victim."

    2. Strengths-Based Approach: Focus on resilience, capabilities, and potential rather than deficits or problems.

    3. Cultural Sensitivity: Recognize and respect diverse cultural backgrounds, beliefs, and experiences.

    4. Empowerment and Choice: Provide options and respect individual autonomy in decision-making.

    5. Safety and Trust: Create psychologically and physically safe environments through consistent, predictable communication.

    6. Collaboration: Work with rather than for people, recognizing their expertise in their own experiences.

    Key Language Considerations:
    - Use "person-first" language consistently
    - Avoid stigmatizing terms like "crazy," "broken," or "damaged"
    - Choose empowering words like "survivor" over "victim" when appropriate
    - Be specific and clear rather than vague
    - Acknowledge strengths and resilience explicitly
    ''',

    'email_communication': '''
    Trauma-Informed Email Communication Guidelines:

    Subject Lines:
    - Be clear and specific, avoid ambiguous or urgent-sounding subjects
    - Use neutral, professional tone
    - Example: "Meeting Follow-up" rather than "URGENT: We Need to Talk"

    Opening:
    - Use warm, professional greetings
    - Acknowledge the person's time and attention
    - Be clear about the purpose upfront

    Body Content:
    - Use clear, straightforward language
    - Break information into digestible chunks
    - Provide context for requests or information
    - Offer choices when possible
    - Be specific about next steps or expectations

    Closing:
    - Express appreciation
    - Provide clear contact information
    - Indicate response timeframes if needed
    - Use supportive, professional sign-offs

    Avoid:
    - Aggressive or demanding language
    - Time pressure unless absolutely necessary
    - Assumptions about the recipient's situation
    - Judgmental or critical tone
    ''',

    'written_communication': '''
    Trauma-Informed Written Content Guidelines:

    Structure and Flow:
    - Use clear headings and subheadings
    - Include content warnings when discussing potentially triggering topics
    - Provide clear navigation and exit strategies
    - Break up long blocks of text

    Language and Tone:
    - Use accessible, jargon-free language
    - Maintain a respectful, non-judgmental tone
    - Include diverse perspectives and experiences
    - Focus on hope and possibility

    Content Considerations:
    - Lead with strengths and resilience
    - Provide practical, actionable information
    - Include resources and support options
    - Acknowledge different experiences and responses
    - Validate feelings and experiences

    Formatting:
    - Use bullet points for key information
    - Include white space for readability
    - Use consistent formatting throughout
    - Consider accessibility needs (font size, contrast)
    ''',

    'social_media_guidelines': '''
    Trauma-Informed Social Media Communication:

    Content Creation:
    - Use content warnings for sensitive topics
    - Focus on empowerment and hope
    - Share resources and support information
    - Highlight diverse voices and experiences
    - Celebrate resilience and recovery

    Engagement:
    - Respond with empathy and respect
    - Avoid giving unsolicited advice
    - Direct people to appropriate resources
    - Maintain professional boundaries
    - Model supportive communication

    Language Choices:
    - Use inclusive, accessible language
    - Avoid sensationalism or dramatic language
    - Choose images and words carefully
    - Consider cultural sensitivity
    - Promote dignity and respect

    Community Building:
    - Foster supportive environments
    - Moderate comments thoughtfully
    - Create safe spaces for sharing
    - Encourage peer support
    - Address harmful content promptly

    Hashtags and Accessibility:
    - Use relevant, supportive hashtags
    - Include image descriptions
    - Consider platform accessibility features
    - Make content searchable for those seeking help
    ''',

    'rewriting_guidelines': '''
    Trauma-Informed Content Rewriting Principles:

    The Gracious Response Approach:
    - Model appropriate language naturally without lecturing or correcting
    - Respond with dignity and respect regardless of original language choices
    - Focus on the user's actual communication goals
    - Incorporate empowering language organically within responses
    - Avoid creating shame or defensiveness through language policing

    Assessment Phase:
    - Identify opportunities to model trauma-informed language
    - Look for ways to naturally incorporate strengths-based framing
    - Check for opportunities to improve accessibility and inclusion
    - Assess how to maintain warmth while being professional

    Graceful Language Integration:
    - Naturally use "person who experienced..." instead of "victim"
    - Organically incorporate "lives with" or "experiences" over "suffers from"
    - Model "healing" or "working through challenges" instead of "broken"
    - Choose "experiencing distress" over stigmatizing terms
    - Emphasize resilience, growth, and possibility

    Tone Modeling:
    - Demonstrate warmth and empathy through example
    - Show non-judgmental approaches in practice
    - Include hope and possibility naturally
    - Acknowledge complexity with compassion
    - Validate experiences while maintaining professional boundaries

    Response Philosophy:
    - Maintain therapeutic relationship through respectful engagement
    - Focus on user needs rather than language correction
    - Model trauma-informed principles through consistent practice
    - Create safe spaces through example rather than instruction
    ''',

    'crisis_communication': '''
    Crisis Communication Guidelines:

    Immediate Response Principles:
    - Prioritize safety and stabilization
    - Use calm, clear, directive language
    - Avoid overwhelming with information
    - Provide immediate next steps
    - Connect to appropriate resources

    Language During Crisis:
    - Use simple, concrete language
    - Repeat important information
    - Avoid jargon or complex instructions
    - Be patient and non-judgmental
    - Validate the person's experience

    Resource Provision:
    - Have crisis resources readily available
    - Provide multiple contact options
    - Include both immediate and long-term resources
    - Consider accessibility needs
    - Follow up when appropriate

    Boundaries and Safety:
    - Know your scope of practice
    - Don't provide services outside your expertise
    - Ensure confidentiality and privacy
    - Document appropriately
    - Seek consultation when needed
    '''
}

# Protocol indexing for easy searching
PROTOCOL_INDEX = {
    'person_first_language': {
        'categories': ['general_principles', 'rewriting_guidelines'],
        'keywords': ['person-first', 'language', 'terminology', 'victim', 'survivor'],
        'description': 'Guidelines for using person-first language that empowers rather than stigmatizes'
    },
    'email_best_practices': {
        'categories': ['email_communication'],
        'keywords': ['email', 'subject', 'greeting', 'professional', 'closing'],
        'description': 'Comprehensive email communication guidelines for trauma-informed organizations'
    },
    'social_media_protocols': {
        'categories': ['social_media_guidelines'],
        'keywords': ['social', 'media', 'content', 'engagement', 'hashtags', 'accessibility'],
        'description': 'Social media communication strategies that prioritize safety and empowerment'
    },
    'crisis_response': {
        'categories': ['crisis_communication'],
        'keywords': ['crisis', 'emergency', 'immediate', 'safety', 'resources'],
        'description': 'Emergency communication protocols for crisis situations'
    },
    'content_rewriting': {
        'categories': ['rewriting_guidelines'],
        'keywords': ['rewrite', 'revision', 'assessment', 'language replacement', 'tone'],
        'description': 'Systematic approach to transforming content to be trauma-informed'
    },
    'written_content_structure': {
        'categories': ['written_communication'],
        'keywords': ['structure', 'headings', 'content warnings', 'formatting', 'accessibility'],
        'description': 'Guidelines for structuring written content in trauma-informed ways'
    },
    'safety_and_trust': {
        'categories': ['general_principles', 'crisis_communication'],
        'keywords': ['safety', 'trust', 'predictable', 'boundaries', 'environment'],
        'description': 'Core principles for creating psychologically and physically safe communications'
    },
    'strengths_based_approach': {
        'categories': ['general_principles', 'rewriting_guidelines'],
        'keywords': ['strengths', 'resilience', 'capabilities', 'empowerment', 'deficit'],
        'description': 'Approaches that focus on strengths and resilience rather than problems'
    },
    'cultural_sensitivity': {
        'categories': ['general_principles', 'social_media_guidelines'],
        'keywords': ['cultural', 'diversity', 'inclusive', 'backgrounds', 'sensitivity'],
        'description': 'Guidelines for culturally responsive and inclusive communication'
    },
    'collaboration_principles': {
        'categories': ['general_principles'],
        'keywords': ['collaboration', 'autonomy', 'choice', 'expertise', 'empowerment'],
        'description': 'Principles for collaborative, empowering communication approaches'
    }
}

# Language replacement dictionary for quick reference
LANGUAGE_REPLACEMENTS = {
    'avoid_terms': {
        'victim': ['person who experienced...', 'survivor (context dependent)'],
        'suffers from': ['lives with', 'experiences'],
        'normal people': ['people without this experience'],
        'crazy': ['experiencing distress', 'specific descriptors'],
        'broken': ['healing', 'working through challenges'],
        'damaged': ['healing', 'resilient'],
        'dysfunctional': ['experiencing challenges', 'working toward wellness'],
        'addict': ['person with substance use disorder'],
        'mentally ill': ['person with mental health condition']
    },
    'preferred_terms': {
        'person-first language': 'Always put the person before their condition',
        'survivor': 'When appropriate and chosen by the individual',
        'resilience': 'Natural human capacity to heal and grow',
        'healing journey': 'Process of recovery and growth',
        'experiencing': 'Rather than "suffering from"',
        'living with': 'For ongoing conditions',
        'working through': 'For active processes'
    }
}

def get_protocol_by_category(category: str) -> str:
    """Get trauma-informed protocol by category"""
    return TRAUMA_INFORMED_KNOWLEDGE.get(category, '')

def search_protocols(query: str) -> dict:
    """Search protocols based on keywords and return relevant matches"""
    query_lower = query.lower()
    matches = {}
    
    for protocol_id, protocol_info in PROTOCOL_INDEX.items():
        # Check if any keywords match
        keyword_matches = any(keyword in query_lower for keyword in protocol_info['keywords'])
        if keyword_matches:
            matches[protocol_id] = {
                'description': protocol_info['description'],
                'categories': protocol_info['categories'],
                'content': [get_protocol_by_category(cat) for cat in protocol_info['categories']]
            }
    
    return matches

def get_language_replacement(term: str) -> list:
    """Get suggested replacements for potentially stigmatizing language"""
    term_lower = term.lower()
    for avoid_term, replacements in LANGUAGE_REPLACEMENTS['avoid_terms'].items():
        if avoid_term in term_lower:
            return replacements
    return []

def validate_trauma_informed_content(content: str) -> dict:
    """Validate content against trauma-informed principles and provide recommendations"""
    issues = []
    recommendations = []
    
    content_lower = content.lower()
    
    # Check for stigmatizing language
    for avoid_term, replacements in LANGUAGE_REPLACEMENTS['avoid_terms'].items():
        if avoid_term in content_lower:
            issues.append(f"Contains potentially stigmatizing term: '{avoid_term}'")
            recommendations.append(f"Consider replacing '{avoid_term}' with: {', '.join(replacements)}")
    
    # Check for person-first language violations
    problematic_phrases = ['trauma victim', 'the mentally ill', 'addicts', 'the disabled']
    for phrase in problematic_phrases:
        if phrase in content_lower:
            issues.append(f"Not using person-first language: '{phrase}'")
            recommendations.append(f"Use person-first language instead of '{phrase}'")
    
    # Check for strengths-based language
    deficit_words = ['broken', 'damaged', 'dysfunctional', 'abnormal']
    deficit_found = [word for word in deficit_words if word in content_lower]
    if deficit_found:
        issues.append(f"Contains deficit-based language: {', '.join(deficit_found)}")
        recommendations.append("Focus on strengths, resilience, and healing rather than deficits")
    
    return {
        'is_trauma_informed': len(issues) == 0,
        'issues': issues,
        'recommendations': recommendations,
        'score': max(0, 100 - (len(issues) * 20))  # Simple scoring system
    }

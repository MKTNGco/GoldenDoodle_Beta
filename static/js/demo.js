// Demo functionality for the homepage
document.addEventListener('DOMContentLoaded', function() {
    const demoInput = document.getElementById('demoInput');
    const demoSendBtn = document.getElementById('demoSendBtn');
    const demoResponseArea = document.getElementById('demoResponseArea');
    const demoResponseContent = document.getElementById('demoResponseContent');
    const demoBrandVoiceBtn = document.getElementById('demoBrandVoiceBtn');
    const demoModeButtons = document.querySelectorAll('.demo-mode-btn');
    const demoMoreBtn = document.getElementById('demoMoreBtn');
    const demoSecondaryModes = document.getElementById('demoSecondaryModes');

    // Check if elements exist before adding event listeners
    if (!demoInput || !demoSendBtn || !demoResponseArea || !demoResponseContent) {
        console.log('Demo elements not found on this page');
        return;
    }

    let selectedMode = 'email'; // default mode

    // Enable/disable send button based on input
    demoInput.addEventListener('input', function() {
        demoSendBtn.disabled = this.value.trim() === '';
    });

    // Auto-resize textarea
    demoInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 500) + 'px';
    });

    // Mode selection
    demoModeButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            demoModeButtons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            // Update selected mode
            selectedMode = this.dataset.mode;
        });
    });

    // Don't set any default active mode - let user choose

    // More button functionality
    if (demoMoreBtn && demoSecondaryModes) {
        demoMoreBtn.addEventListener('click', function() {
            const isExpanded = demoSecondaryModes.classList.contains('show');
            demoSecondaryModes.classList.toggle('show');
            demoMoreBtn.classList.toggle('expanded');
        });
    }

    // Brand voice button (premium feature demo)
    if (demoBrandVoiceBtn) {
        demoBrandVoiceBtn.addEventListener('click', function() {
            // Show premium feature message
            showPremiumMessage();
        });
    }

    // Send button functionality
    demoSendBtn.addEventListener('click', function() {
        const inputText = demoInput.value.trim();
        if (!inputText) return;

        // Store the demo prompt and mode in sessionStorage for the chat page
        sessionStorage.setItem('demoPrompt', inputText);
        sessionStorage.setItem('demoMode', selectedMode);

        // Redirect to chat page
        window.location.href = '/chat';
    });

    // Enter key to send (Shift+Enter for new line)
    demoInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!demoSendBtn.disabled) {
                demoSendBtn.click();
            }
        }
    });

    function showDemoResponse(inputText, mode) {
        const responses = {
            email: `Subject: Supporting Our Community Together

Dear Friend,

Thank you for reaching out about supporting our mission. Your interest in helping our community means so much to us.

We understand that choosing where to direct your support is a meaningful decision. Our work focuses on creating safe spaces where healing can happen naturally, at each person's own pace.

Your contribution would help us continue providing trauma-informed services that prioritize dignity, choice, and empowerment for everyone we serve.

If you'd like to learn more about our approach or have any questions, please don't hesitate to reach out. We're here to listen and support you in whatever way feels right.

With gratitude,
[Your Organization]`,

            article: `# Creating Trauma-Informed Spaces: A Community Approach

In our work with survivors, we've learned that healing happens best in environments that prioritize safety, trust, and choice. Every interaction matters, and every space we create has the potential to support someone's journey toward wellness.

## What Makes a Space Trauma-Informed?

Trauma-informed spaces recognize that many people carry invisible wounds. They're designed with the understanding that past experiences shape how we move through the world today.

Key principles include:
- **Safety first** - Both physical and emotional security
- **Trustworthiness** - Clear, consistent communication
- **Choice** - Empowering people to make their own decisions
- **Cultural responsiveness** - Honoring diverse experiences and backgrounds

## Building These Spaces Together

Creating trauma-informed environments isn't just about policies—it's about changing how we see and interact with each other. It requires ongoing commitment, learning, and community partnership.

When we center these principles in our work, we create spaces where healing can flourish naturally.`,

            social_media: `🌱 Healing happens in community. 

Today we're reflecting on what it means to create spaces where everyone feels safe, heard, and valued. 

Your story matters. Your healing matters. You matter. 

#TraumaInformed #CommunityHealing #SafeSpaces #NonprofitLife`,

            rewrite: `Here's a trauma-informed revision of your text:

**Original approach:** Direct request for action
**Trauma-informed approach:** Invitation with choice

Instead of "You must attend this meeting," try:
"We'd love to have you join us for this gathering. We understand everyone has different comfort levels and needs, so please join in whatever way feels right for you—whether that's in person, virtually, or simply staying connected through updates."

This revision:
✓ Offers choice and flexibility
✓ Acknowledges different comfort levels  
✓ Provides multiple ways to participate
✓ Uses inclusive, welcoming language`,

            summarize: `## Key Points Summary

**Trauma-Informed Communication Principles:**
• Safety first - creating secure emotional and physical environments
• Trust building through consistent, transparent communication  
• Empowerment through choice and collaboration
• Cultural humility and responsiveness

**Practical Applications:**
• Use invitational rather than demanding language
• Provide multiple engagement options
• Acknowledge different comfort levels
• Center dignity and respect in all interactions

**Impact:** These approaches create spaces where healing can happen naturally while honoring each person's unique journey and needs.`,

            brainstorm: `## Content Ideas for Trauma-Informed Communications

**Email Campaigns:**
• Survivor story highlights (with permission)
• Educational series on trauma-informed principles
• Community resource roundups
• Gentle fundraising appeals

**Social Media:**
• Daily affirmations and healing quotes
• Behind-the-scenes glimpses of your work
• Partner organization spotlights
• Awareness day posts

**Articles & Blog Posts:**
• "Understanding Secondary Trauma"
• "Creating Safe Spaces in Your Community"
• "The Science of Healing"
• "Building Resilience Together"

**Event Ideas:**
• Trauma-informed care workshops
• Community healing circles
• Professional development sessions
• Awareness campaigns`,

            analyze: `## Communication Analysis & Recommendations

**Current Strengths:**
✓ Uses person-first language
✓ Acknowledges individual experiences
✓ Provides multiple engagement pathways

**Areas for Enhancement:**
⚡ Increase use of collaborative language
⚡ Add more choice-oriented phrasing
⚡ Include cultural responsiveness elements

**Trauma-Informed Score: 8/10**

**Specific Improvements:**
• Replace "you should" with "you might consider"
• Add "if this feels right for you" to suggestions
• Include diverse representation in examples
• Offer alternative ways to engage

**Emotional Safety Level: High**
Your communication prioritizes emotional safety while maintaining clear, helpful information.`,

            outreach: `Subject: Partnership Opportunity - Trauma-Informed Community Building

Dear [Organization Name],

We hope this message finds you well. We're reaching out because we deeply admire the work you do in supporting our community.

At [Your Organization], we're exploring opportunities to collaborate with like-minded organizations who share our commitment to trauma-informed care and community healing.

We'd love to learn more about your current initiatives and explore how we might support each other's missions. Whether that's through resource sharing, joint programming, or simply connecting our communities, we believe there's strength in working together.

If a conversation feels right for your organization, we'd be honored to connect. Please feel free to reach out at your convenience, or let us know if you'd prefer to receive updates about our work instead.

With gratitude and respect,
[Your Team]`,

            memo: `**MEMO**

**To:** Team Leadership
**From:** Communications Team  
**Date:** [Current Date]
**Re:** Trauma-Informed Communication Guidelines

**Purpose:**
This memo outlines key principles for maintaining trauma-informed approaches in all organizational communications.

**Key Guidelines:**
• **Language Choices:** Use invitational rather than directive phrasing
• **Accessibility:** Provide multiple ways for people to engage
• **Safety:** Prioritize emotional and psychological safety in messaging
• **Choice:** Always offer options and respect boundaries

**Implementation:**
All outward-facing communications should be reviewed using our trauma-informed checklist before distribution.

**Resources:**
Training materials and templates are available on our shared drive. Please contact the Communications team with questions.

Thank you for your continued commitment to creating healing spaces through our communications.`,

            grant_proposal: `**Project Title:** Community Healing Initiative

**Executive Summary**
Our organization requests $[Amount] to expand trauma-informed communication training throughout our community network. This initiative will build capacity among local nonprofits to create safer, more inclusive spaces for healing.

**Project Description**
The Community Healing Initiative will provide comprehensive training on trauma-informed communication principles to 25 local nonprofit organizations, reaching an estimated 500 community members.

**Goals & Objectives**
• Train 75 nonprofit staff in trauma-informed communication
• Develop culturally responsive communication resources
• Create peer support networks for ongoing learning
• Establish community-wide standards for healing-centered communication

**Expected Outcomes**
Participants will demonstrate increased knowledge of trauma-informed principles and report greater confidence in creating safe, inclusive communication environments.

**Budget Summary**
Training materials: $[Amount]
Facilitator fees: $[Amount]  
Resource development: $[Amount]
Evaluation: $[Amount]

This investment will create lasting change in how our community approaches healing-centered communication.`
        };

        demoResponseContent.innerHTML = responses[mode] || responses.email;
        demoResponseArea.style.display = 'block';
        demoResponseArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function showPremiumMessage() {
        // Show a tooltip-like message for premium features
        const tooltip = document.createElement('div');
        tooltip.innerHTML = `
            <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: var(--charcoal); color: var(--cloud-white); padding: 16px 20px; border-radius: 8px; font-size: 0.9rem; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                <i class="fas fa-crown" style="color: #fbbf24; margin-right: 8px;"></i>
                This feature is available with a free account!
                <div style="margin-top: 8px;">
                    <a href="/register" style="color: var(--clearwater-teal); text-decoration: underline;">Sign up now</a>
                </div>
            </div>
        `;

        document.body.appendChild(tooltip);

        // Remove after 3 seconds
        setTimeout(() => {
            if (tooltip.parentNode) {
                tooltip.parentNode.removeChild(tooltip);
            }
        }, 3000);
    }
});

// Global functions for demo response actions
function copyDemoResponse() {
    const content = document.getElementById('demoResponseContent');
    if (content) {
        navigator.clipboard.writeText(content.textContent).then(() => {
            // Show success message
            const btn = event.target.closest('.demo-copy-btn');
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>';
            btn.style.background = 'var(--clearwater-teal)';
            btn.style.color = 'white';

            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.style.background = '';
                btn.style.color = '';
            }, 2000);
        });
    }
}

function clearDemoResponse() {
    const responseArea = document.getElementById('demoResponseArea');
    if (responseArea) {
        responseArea.style.display = 'none';
    }
}
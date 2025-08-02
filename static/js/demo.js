// Demo functionality for the homepage
document.addEventListener('DOMContentLoaded', function() {
    const demoInput = document.getElementById('demoInput');
    const demoSendBtn = document.getElementById('demoSendBtn');
    const demoResponseArea = document.getElementById('demoResponseArea');
    const demoResponseContent = document.getElementById('demoResponseContent');
    const demoBrandVoiceBtn = document.getElementById('demoBrandVoiceBtn');
    const demoModeButtons = document.querySelectorAll('.demo-mode-btn');

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

    // Set default active mode
    if (demoModeButtons.length > 0) {
        demoModeButtons[0].classList.add('active');
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

        // Show loading state
        demoSendBtn.disabled = true;
        demoSendBtn.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div>';

        // Simulate AI response after a delay
        setTimeout(() => {
            showDemoResponse(inputText, selectedMode);

            // Reset button
            demoSendBtn.disabled = false;
            demoSendBtn.innerHTML = '<svg class="send-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>';

            // Clear input
            demoInput.value = '';
            demoInput.style.height = 'auto';
        }, 2000);
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
✓ Uses inclusive, welcoming language`
        };

        demoResponseContent.innerHTML = responses[mode] || responses.email;
        demoResponseArea.style.display = 'block';
        demoResponseArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function showPremiumMessage() {
        // Create a temporary tooltip-like message
        const message = document.createElement('div');
        message.innerHTML = `
            <div style="position: absolute; top: 100%; left: 0; background: var(--charcoal); color: var(--cloud-white); padding: 8px 12px; border-radius: 8px; font-size: 0.875rem; white-space: nowrap; z-index: 1000; margin-top: 4px;">
                <i class="fas fa-crown" style="color: #fbbf24; margin-right: 6px;"></i>
                Brand Voice is a premium feature - Sign up to get started!
                <div style="position: absolute; top: -4px; left: 12px; width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 4px solid var(--charcoal);"></div>
            </div>
        `;

        demoBrandVoiceBtn.style.position = 'relative';
        demoBrandVoiceBtn.appendChild(message);

        // Remove message after 3 seconds
        setTimeout(() => {
            if (message.parentNode) {
                message.parentNode.removeChild(message);
            }
        }, 3000);
    }
});
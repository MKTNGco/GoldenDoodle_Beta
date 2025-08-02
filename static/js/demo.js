
// GoldenDoodleLM Demo Interface
class DemoInterface {
    constructor() {
        this.currentMode = 'email';
        this.isGenerating = false;
        this.placeholderIndex = 0;
        this.placeholderInterval = null;
        
        this.placeholders = [
            "Try me! Write a trauma-informed email to donors...",
            "Create a compassionate program announcement...",
            "Draft sensitive client communication...",
            "Brainstorm inclusive fundraising ideas...",
            "Analyze survey data with privacy protection...",
            "Rewrite this content with trauma awareness...",
            "Generate healing-centered messaging...",
            "Create accessible program materials..."
        ];
        
        this.sampleResponses = {
            email: "Here's a trauma-informed email draft:\n\nSubject: You're Invited to Join Our Supportive Community\n\nDear Friend,\n\nWe hope this message finds you in a moment of peace. We're reaching out to share an opportunity that we believe could be meaningful for you.\n\nOur new support group creates a safe, confidential space where survivors can connect, share experiences, and support one another on their healing journey. This group is entirely voluntary and designed to honor your autonomy and choices.\n\nWhat to expect:\n• A welcoming, judgment-free environment\n• Trained facilitators who understand trauma\n• Flexible participation - attend when it feels right for you\n• Confidentiality and respect for all participants\n\nYou are the expert of your own experience, and this group exists to support you in whatever way feels helpful. There's no pressure to participate, and you can join or step back at any time.\n\nIf you'd like to learn more, please feel free to reach out. We're here to answer any questions and support you in making the best decision for yourself.\n\nWith care and respect,\n[Your Organization]",
            
            article: "# Creating Trauma-Informed Workplaces: A Guide for Nonprofit Leaders\n\nBuilding a trauma-informed workplace isn't just about policies—it's about creating a culture where everyone feels safe, valued, and empowered to do their best work.\n\n## Understanding Trauma's Impact\n\nTrauma affects people differently, and its effects can show up in various ways in the workplace. By understanding this, we can create environments that support healing and resilience rather than inadvertently causing re-traumatization.\n\n## Key Principles for Implementation\n\n**Safety First**: Both physical and emotional safety should be prioritized in all workplace interactions and policies.\n\n**Building Trust**: Consistency, transparency, and follow-through help build the trust necessary for a healthy work environment.\n\n**Empowerment**: Provide opportunities for staff to have voice and choice in their work and workplace policies.\n\n**Cultural Responsiveness**: Recognize and honor the diverse backgrounds and experiences of all team members.\n\n## Practical Steps\n\n1. **Training and Education**: Provide trauma-informed care training for all staff\n2. **Policy Review**: Examine existing policies through a trauma-informed lens\n3. **Environment**: Create physical spaces that feel welcoming and safe\n4. **Communication**: Use clear, respectful communication that acknowledges people's experiences\n\nRemember, becoming trauma-informed is an ongoing journey, not a destination. Every step toward greater understanding and compassion makes a difference.",
            
            social_media: "🌟 Your resilience inspires us every day. 🌟\n\nAt [Your Organization], we believe in the power of community and the strength that comes from supporting one another. Whether you're taking your first step toward healing or you've been on this journey for years, you belong here.\n\n💙 You are valued\n💙 You are heard\n💙 You matter\n\nTogether, we're creating spaces where everyone can thrive. Thank you for being part of our community.\n\n#TraumaInformed #CommunitySupport #Healing #NonprofitLife #YouMatter",
            
            rewrite: "Here's a trauma-informed rewrite of your content:\n\n**Original approach:** \"You must attend all sessions to benefit from our program.\"\n\n**Trauma-informed rewrite:** \"We've designed our program to be as flexible as possible while still providing meaningful support. While we encourage regular participation to help build connections and continuity, we understand that life circumstances vary. You're welcome to participate in whatever way works best for you, and our team is here to help you navigate any challenges that might arise.\"\n\n**Key changes made:**\n• Removed demanding language (\"must\")\n• Acknowledged individual circumstances\n• Maintained program structure while offering flexibility\n• Emphasized support rather than requirements\n• Used collaborative language (\"we\" vs \"you\")\n\nThis approach honors people's autonomy while still communicating the value of consistent participation."
        };
        
        this.initializeElements();
        this.bindEvents();
        this.autoResizeTextarea();
        this.startPlaceholderRotation();
        this.updateSendButton();
        this.selectMode(document.querySelector('.demo-mode-btn[data-mode="email"]'));
    }

    initializeElements() {
        this.demoInput = document.getElementById('demoInput');
        this.demoSendBtn = document.getElementById('demoSendBtn');
        this.demoBrandVoiceBtn = document.getElementById('demoBrandVoiceBtn');
        this.demoResponseArea = document.getElementById('demoResponseArea');
        this.demoResponseContent = document.getElementById('demoResponseContent');
        this.modeButtons = document.querySelectorAll('.demo-mode-btn[data-mode]');
    }

    bindEvents() {
        // Textarea events
        this.demoInput.addEventListener('input', () => {
            this.autoResizeTextarea();
            this.updateSendButton();
        });
        
        this.demoInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendDemoMessage();
            }
        });

        this.demoInput.addEventListener('focus', () => {
            this.stopPlaceholderRotation();
        });

        this.demoInput.addEventListener('blur', () => {
            if (!this.demoInput.value.trim()) {
                this.startPlaceholderRotation();
            }
        });

        // Send button
        this.demoSendBtn.addEventListener('click', () => this.sendDemoMessage());

        // Brand voice button (premium feature demo)
        this.demoBrandVoiceBtn.addEventListener('click', () => {
            this.showPremiumFeatureModal();
        });

        // Attachment button (premium feature demo)
        document.querySelector('.demo-attachment-btn').addEventListener('click', () => {
            this.showPremiumFeatureModal();
        });

        // Mode buttons
        this.modeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.selectMode(btn));
        });
    }

    autoResizeTextarea() {
        this.demoInput.style.height = 'auto';
        const scrollHeight = this.demoInput.scrollHeight;
        const maxHeight = 200;
        
        if (scrollHeight > maxHeight) {
            this.demoInput.style.height = maxHeight + 'px';
            this.demoInput.style.overflowY = 'auto';
        } else {
            this.demoInput.style.height = Math.max(scrollHeight, 40) + 'px';
            this.demoInput.style.overflowY = 'hidden';
        }
    }

    startPlaceholderRotation() {
        if (this.placeholderInterval) return;
        
        this.placeholderInterval = setInterval(() => {
            this.placeholderIndex = (this.placeholderIndex + 1) % this.placeholders.length;
            this.demoInput.placeholder = this.placeholders[this.placeholderIndex];
        }, 4000);
    }

    stopPlaceholderRotation() {
        if (this.placeholderInterval) {
            clearInterval(this.placeholderInterval);
            this.placeholderInterval = null;
        }
    }

    selectMode(button) {
        const mode = button.dataset.mode;
        
        this.modeButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        this.currentMode = mode;
    }

    updateSendButton() {
        const hasText = this.demoInput.value.trim().length > 0;
        this.demoSendBtn.disabled = !hasText || this.isGenerating;
    }

    async sendDemoMessage() {
        const prompt = this.demoInput.value.trim();
        
        if (!prompt || this.isGenerating) {
            return;
        }

        // Update UI
        this.isGenerating = true;
        this.updateSendButton();
        this.updateSendButtonLoading(true);

        // Show loading
        this.demoResponseArea.style.display = 'block';
        this.demoResponseContent.innerHTML = '<div class="loading-dots">Generating trauma-informed response...</div>';

        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Show response based on current mode
        const response = this.sampleResponses[this.currentMode] || this.sampleResponses.email;
        this.demoResponseContent.innerHTML = this.formatMessage(response);

        // Add call-to-action
        setTimeout(() => {
            const ctaHtml = `
                <div class="demo-cta mt-3 p-3 bg-light rounded">
                    <h6 class="fw-bold text-primary mb-2">👋 Like what you see?</h6>
                    <p class="mb-2 small">This is just a taste of what GoldenDoodleLM can do. Create a free account to:</p>
                    <ul class="small mb-3">
                        <li>Use custom brand voices</li>
                        <li>Access all content modes</li>
                        <li>Upload and analyze documents</li>
                        <li>Get unlimited generations</li>
                    </ul>
                    <a href="/register" class="btn btn-primary btn-sm">Get Started Free</a>
                </div>
            `;
            this.demoResponseContent.innerHTML += ctaHtml;
        }, 1000);

        // Reset UI
        this.isGenerating = false;
        this.updateSendButton();
        this.updateSendButtonLoading(false);
        this.demoInput.value = '';
        this.autoResizeTextarea();
    }

    updateSendButtonLoading(isLoading) {
        if (isLoading) {
            this.demoSendBtn.innerHTML = `
                <svg class="send-icon loading-spinner" viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25"/>
                    <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
            `;
        } else {
            this.demoSendBtn.innerHTML = `
                <svg class="send-icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
            `;
        }
    }

    showPremiumFeatureModal() {
        // Create a simple modal overlay
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        `;
        
        modal.innerHTML = `
            <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 400px; text-align: center; margin: 1rem;">
                <div style="color: #fbbf24; font-size: 2rem; margin-bottom: 1rem;">
                    <i class="fas fa-crown"></i>
                </div>
                <h5 style="color: #1f2937; margin-bottom: 1rem;">Premium Feature</h5>
                <p style="color: #6b7280; margin-bottom: 1.5rem;">Brand voices and file attachments are available with a free account. Sign up to unlock all features!</p>
                <div style="display: flex; gap: 0.5rem; justify-content: center;">
                    <a href="/register" class="btn btn-primary">Get Started Free</a>
                    <button class="btn btn-outline-secondary" onclick="this.closest('[style*=fixed]').remove()">Close</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    formatMessage(content) {
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>')
            .replace(/<p><\/p>/g, '');
    }
}

// Initialize demo interface
document.addEventListener('DOMContentLoaded', function() {
    new DemoInterface();
});

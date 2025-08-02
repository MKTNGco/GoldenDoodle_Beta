// GoldenDoodleLM Chat Interface
class ChatInterface {
    constructor() {
        this.currentMode = null;
        this.isGenerating = false;
        this.initializeElements();
        this.bindEvents();
        this.updatePlaceholder();
    }

    initializeElements() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.brandVoiceSelect = document.getElementById('brandVoiceSelect');
        this.modeButtons = document.querySelectorAll('.mode-btn');
        this.moreModesBtn = document.getElementById('moreModesBtn');
        this.secondaryModes = document.getElementById('secondaryModes');
    }

    bindEvents() {
        // Send button click
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        
        // Enter key in textarea
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Mode button clicks
        this.modeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.selectMode(btn));
        });

        // More modes toggle
        this.moreModesBtn.addEventListener('click', () => this.toggleMoreModes());

        // Brand voice change
        this.brandVoiceSelect.addEventListener('change', () => this.updatePlaceholder());
    }

    selectMode(button) {
        const mode = button.dataset.mode;
        
        // Toggle mode selection
        if (this.currentMode === mode) {
            // Deselect current mode
            this.currentMode = null;
            button.classList.remove('active');
        } else {
            // Select new mode
            this.modeButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            this.currentMode = mode;
        }
        
        this.updatePlaceholder();
    }

    toggleMoreModes() {
        const isVisible = this.secondaryModes.style.display !== 'none';
        
        if (isVisible) {
            this.secondaryModes.style.display = 'none';
            this.moreModesBtn.innerHTML = '<i class="fas fa-ellipsis-h me-1"></i>More';
        } else {
            this.secondaryModes.style.display = 'block';
            this.moreModesBtn.innerHTML = '<i class="fas fa-times me-1"></i>Less';
        }
    }

    updatePlaceholder() {
        const modePlaceholders = {
            'email': 'Compose a professional, empathetic email...',
            'article': 'Write an informative article with trauma-informed principles...',
            'social_media': 'Create engaging, accessible social media content...',
            'rewrite': 'Transform existing content with trauma-informed enhancements...',
            'summarize': 'Summarize this document or content...',
            'brainstorm': 'Let\'s brainstorm creative ideas...',
            'analyze': 'Analyze this data or content...'
        };

        let placeholder = 'How can I help you create trauma-informed content today?';
        
        if (this.currentMode && modePlaceholders[this.currentMode]) {
            placeholder = modePlaceholders[this.currentMode];
        }

        const brandVoice = this.brandVoiceSelect.options[this.brandVoiceSelect.selectedIndex].text;
        if (this.brandVoiceSelect.value) {
            placeholder += ` (Using ${brandVoice})`;
        }

        this.chatInput.placeholder = placeholder;
    }

    async sendMessage() {
        const prompt = this.chatInput.value.trim();
        
        if (!prompt || this.isGenerating) {
            return;
        }

        // Clear input and disable send button
        this.chatInput.value = '';
        this.isGenerating = true;
        this.updateSendButton();

        // Add user message to chat
        this.addMessage(prompt, 'user');

        // Add loading message
        const loadingId = this.addLoadingMessage();

        try {
            // Prepare request data
            const requestData = {
                prompt: prompt,
                content_mode: this.currentMode,
                brand_voice_id: this.brandVoiceSelect.value || null
            };

            // Send request to backend
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();

            // Remove loading message
            this.removeLoadingMessage(loadingId);

            if (response.ok) {
                // Add AI response
                this.addMessage(data.response, 'ai');
            } else {
                // Add error message
                this.addMessage(data.error || 'Sorry, I encountered an error. Please try again.', 'ai', true);
            }

        } catch (error) {
            console.error('Error generating content:', error);
            this.removeLoadingMessage(loadingId);
            this.addMessage('I apologize, but I\'m having trouble connecting right now. Please try again in a moment.', 'ai', true);
        }

        // Re-enable interface
        this.isGenerating = false;
        this.updateSendButton();
        this.chatInput.focus();
    }

    addMessage(content, sender, isError = false) {
        // Clear welcome message if this is the first message
        const welcomeMessage = this.chatMessages.querySelector('.text-center.py-5');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${sender} fade-in`;

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = `message-bubble ${isError ? 'border-danger text-danger' : ''}`;
        
        if (sender === 'ai') {
            // Format AI messages with proper line breaks
            bubbleDiv.innerHTML = this.formatMessage(content);
        } else {
            bubbleDiv.textContent = content;
        }

        messageDiv.appendChild(bubbleDiv);
        this.chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

        return messageDiv;
    }

    addLoadingMessage() {
        const loadingId = 'loading-' + Date.now();
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message message-ai';
        messageDiv.id = loadingId;

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        bubbleDiv.innerHTML = '<span class="loading-dots">Thinking</span>';

        messageDiv.appendChild(bubbleDiv);
        this.chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

        return loadingId;
    }

    removeLoadingMessage(loadingId) {
        const loadingMessage = document.getElementById(loadingId);
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }

    updateSendButton() {
        if (this.isGenerating) {
            this.sendBtn.disabled = true;
            this.sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        } else {
            this.sendBtn.disabled = false;
            this.sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }
    }

    formatMessage(content) {
        // Convert markdown-style formatting to HTML
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

// Initialize chat interface
document.addEventListener('DOMContentLoaded', function() {
    new ChatInterface();
});

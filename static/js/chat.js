
// GoldenDoodleLM Modern Chat Interface
class ChatInterface {
    constructor() {
        this.currentMode = null;
        this.isGenerating = false;
        this.selectedBrandVoice = '';
        this.selectedVoiceName = 'Neutral Voice';
        this.placeholderIndex = 0;
        this.placeholderInterval = null;
        
        this.placeholders = [
            "Write a trauma-informed email to donors...",
            "Create a compassionate program announcement...",
            "Draft sensitive client communication...",
            "Play with GoldenDoodleLM - try any prompt!",
            "Brainstorm inclusive fundraising ideas...",
            "Speak with GoldenDoodleLM about your needs...",
            "Analyze survey data with privacy protection...",
            "Fetch me a social media post for our cause...",
            "Rewrite this content with trauma awareness...",
            "Summarize this report for our board...",
            "Generate healing-centered messaging...",
            "Create accessible program materials...",
            "Draft culturally responsive outreach...",
            "Fetch me an article about community impact..."
        ];
        
        this.initializeElements();
        this.bindEvents();
        this.autoResizeTextarea();
        this.startPlaceholderRotation();
        this.updateSendButton();
    }

    initializeElements() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.brandVoiceBtn = document.getElementById('brandVoiceBtn');
        this.brandVoiceDropdown = document.getElementById('brandVoiceDropdown');
        this.selectedVoiceNameElement = document.getElementById('selectedVoiceName');
        this.modeButtons = document.querySelectorAll('.mode-btn[data-mode]');
        this.moreModesBtn = document.getElementById('moreModesBtn');
        this.secondaryModes = document.getElementById('secondaryModes');
    }

    bindEvents() {
        // Textarea events
        this.chatInput.addEventListener('input', () => {
            this.autoResizeTextarea();
            this.updateSendButton();
        });
        
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.chatInput.addEventListener('focus', () => {
            this.stopPlaceholderRotation();
        });

        this.chatInput.addEventListener('blur', () => {
            if (!this.chatInput.value.trim()) {
                this.startPlaceholderRotation();
            }
        });

        // Send button
        this.sendBtn.addEventListener('click', () => this.sendMessage());

        // Attachment button
        document.querySelector('.attachment-btn').addEventListener('click', () => {
            this.handleAttachment();
        });

        // Brand voice selector
        this.brandVoiceBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleBrandVoiceDropdown();
        });

        // Brand voice options
        document.querySelectorAll('.brand-voice-option').forEach(option => {
            option.addEventListener('click', () => {
                this.selectBrandVoice(option.dataset.value, option.textContent);
            });
        });

        // Mode buttons
        this.modeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.selectMode(btn));
        });

        // More modes toggle
        this.moreModesBtn.addEventListener('click', () => this.toggleMoreModes());

        // Global click to close dropdown
        document.addEventListener('click', () => {
            this.closeBrandVoiceDropdown();
        });
    }

    autoResizeTextarea() {
        this.chatInput.style.height = 'auto';
        const scrollHeight = this.chatInput.scrollHeight;
        const maxHeight = 200; // Max height in pixels
        
        if (scrollHeight > maxHeight) {
            this.chatInput.style.height = maxHeight + 'px';
            this.chatInput.style.overflowY = 'auto';
        } else {
            this.chatInput.style.height = Math.max(scrollHeight, 40) + 'px';
            this.chatInput.style.overflowY = 'hidden';
        }
    }

    startPlaceholderRotation() {
        if (this.placeholderInterval) return;
        
        this.placeholderInterval = setInterval(() => {
            this.placeholderIndex = (this.placeholderIndex + 1) % this.placeholders.length;
            this.chatInput.placeholder = this.placeholders[this.placeholderIndex];
        }, 3000);
    }

    stopPlaceholderRotation() {
        if (this.placeholderInterval) {
            clearInterval(this.placeholderInterval);
            this.placeholderInterval = null;
        }
    }

    toggleBrandVoiceDropdown() {
        this.brandVoiceDropdown.classList.toggle('show');
    }

    closeBrandVoiceDropdown() {
        this.brandVoiceDropdown.classList.remove('show');
    }

    selectBrandVoice(value, name) {
        this.selectedBrandVoice = value;
        this.selectedVoiceName = name;
        this.selectedVoiceNameElement.textContent = name;
        this.closeBrandVoiceDropdown();
    }

    selectMode(button) {
        const mode = button.dataset.mode;
        
        if (this.currentMode === mode) {
            this.currentMode = null;
            button.classList.remove('active');
        } else {
            this.modeButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            this.currentMode = mode;
        }
    }

    toggleMoreModes() {
        const isVisible = this.secondaryModes.classList.contains('show');
        
        if (isVisible) {
            this.secondaryModes.classList.remove('show');
            this.moreModesBtn.innerHTML = `
                <svg class="mode-icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M6 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm12 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm-6 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
                </svg>
                More
            `;
        } else {
            this.secondaryModes.classList.add('show');
            this.moreModesBtn.innerHTML = `
                <svg class="mode-icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
                </svg>
                Less
            `;
        }
    }

    updateSendButton() {
        const hasText = this.chatInput.value.trim().length > 0;
        this.sendBtn.disabled = !hasText || this.isGenerating;
    }

    async sendMessage() {
        const prompt = this.chatInput.value.trim();
        
        if (!prompt || this.isGenerating) {
            return;
        }

        // Clear input and update UI
        this.chatInput.value = '';
        this.autoResizeTextarea();
        this.isGenerating = true;
        this.updateSendButton();
        this.updateSendButtonLoading(true);

        // Clear welcome screen if present
        this.clearWelcomeScreen();

        // Add user message
        this.addMessage(prompt, 'user');

        // Add loading message
        const loadingId = this.addLoadingMessage();

        try {
            const requestData = {
                prompt: prompt,
                content_mode: this.currentMode,
                brand_voice_id: this.selectedBrandVoice || null
            };

            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();
            this.removeLoadingMessage(loadingId);

            if (response.ok) {
                this.addMessage(data.response, 'ai');
            } else {
                this.addMessage(data.error || 'Sorry, I encountered an error. Please try again.', 'ai', true);
            }

        } catch (error) {
            console.error('Error generating content:', error);
            this.removeLoadingMessage(loadingId);
            this.addMessage('I apologize, but I\'m having trouble connecting right now. Please try again in a moment.', 'ai', true);
        }

        // Reset UI
        this.isGenerating = false;
        this.updateSendButton();
        this.updateSendButtonLoading(false);
        this.chatInput.focus();
    }

    clearWelcomeScreen() {
        const welcomeScreen = this.chatMessages.querySelector('.welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.remove();
        }
    }

    addMessage(content, sender, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${sender} fade-in`;

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = `message-bubble ${isError ? 'error' : ''}`;
        
        if (sender === 'ai') {
            bubbleDiv.innerHTML = this.formatMessage(content);
        } else {
            bubbleDiv.textContent = content;
        }

        messageDiv.appendChild(bubbleDiv);
        
        // Add to chat content
        let chatContent = this.chatMessages.querySelector('.chat-content');
        if (!chatContent) {
            chatContent = document.createElement('div');
            chatContent.className = 'chat-content';
            this.chatMessages.appendChild(chatContent);
        }
        
        chatContent.appendChild(messageDiv);
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
        bubbleDiv.innerHTML = '<span class="loading-dots">Thinking...</span>';

        messageDiv.appendChild(bubbleDiv);
        
        let chatContent = this.chatMessages.querySelector('.chat-content');
        if (!chatContent) {
            chatContent = document.createElement('div');
            chatContent.className = 'chat-content';
            this.chatMessages.appendChild(chatContent);
        }
        
        chatContent.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

        return loadingId;
    }

    removeLoadingMessage(loadingId) {
        const loadingMessage = document.getElementById(loadingId);
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }

    updateSendButtonLoading(isLoading) {
        if (isLoading) {
            this.sendBtn.innerHTML = `
                <svg class="send-icon loading-spinner" viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25"/>
                    <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
            `;
        } else {
            this.sendBtn.innerHTML = `
                <svg class="send-icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
            `;
        }
    }

    handleAttachment() {
        // Create a hidden file input
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.txt,.pdf,.doc,.docx,.md';
        fileInput.style.display = 'none';
        
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.processAttachment(file);
            }
        });
        
        document.body.appendChild(fileInput);
        fileInput.click();
        document.body.removeChild(fileInput);
    }

    async processAttachment(file) {
        // Check file size (limit to 5MB)
        if (file.size > 5 * 1024 * 1024) {
            alert('File size must be less than 5MB');
            return;
        }

        try {
            const text = await this.readFileAsText(file);
            const truncatedText = text.substring(0, 2000); // Limit to first 2000 characters
            
            // Add the file content to the chat input
            const currentText = this.chatInput.value;
            const newText = currentText + (currentText ? '\n\n' : '') + 
                           `[Attached file: ${file.name}]\n${truncatedText}${text.length > 2000 ? '\n...(truncated)' : ''}`;
            
            this.chatInput.value = newText;
            this.autoResizeTextarea();
            this.updateSendButton();
            this.chatInput.focus();
            
        } catch (error) {
            console.error('Error reading file:', error);
            alert('Error reading file. Please try again.');
        }
    }

    readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(e);
            reader.readAsText(file);
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

// New chat functionality
function startNewChat() {
    // Clear the chat messages
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = `
        <div class="chat-content">
            <div class="welcome-screen">
                <h1>GoldenDoodleLM</h1>
                <p>Your empathetic, trauma-informed AI assistant is here to help create meaningful communications that prioritize safety, trust, and healing.</p>
            </div>
        </div>
    `;
    
    // Focus on the input
    document.getElementById('chatInput').focus();
}

// Initialize chat interface
document.addEventListener('DOMContentLoaded', function() {
    new ChatInterface();
});

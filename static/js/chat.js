// GoldenDoodleLM Modern Chat Interface
class ChatInterface {
    constructor() {
        this.currentMode = null;
        this.isGenerating = false;
        this.selectedBrandVoice = '';
        this.selectedVoiceName = 'Neutral Voice';
        this.placeholderIndex = 0;
        this.placeholderInterval = null;
        this.isDemoMode = window.isDemoMode || false;
        this.isLoggedIn = window.isLoggedIn || false;

        this.placeholders = [
            "Message GoldenDoodleLM...",
            "Write a trauma-informed email...",
            "Create compassionate content...",
            "Draft sensitive communication...",
            "Brainstorm inclusive ideas...",
            "Analyze with privacy protection...",
            "Generate healing-centered messaging...",
            "Create accessible materials...",
            "Draft culturally responsive outreach..."
        ];

        // Only initialize if we're on the chat page
        if (this.initializeElements()) {
            this.bindEvents();
            this.autoResizeTextarea();
            this.startPlaceholderRotation();
            this.updateSendButton();
            this.handleInitialPrompt();
            this.setupDemoMode();
        }
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

        // Check if we're on the chat page
        if (!this.chatInput || !this.sendBtn || !this.chatMessages) {
            console.log('Chat elements not found - not on chat page');
            return false;
        }
        return true;
    }

    bindEvents() {
        // Textarea events
        if (this.chatInput) {
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
        }

        // Send button
        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', () => this.sendMessage());
        }

        // Attachment button
        const attachmentBtn = document.querySelector('.attachment-btn');
        if (attachmentBtn) {
            attachmentBtn.addEventListener('click', () => {
                this.handleAttachment();
            });
        }

        // Brand voice selector
        if (this.brandVoiceBtn) {
            this.brandVoiceBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Brand voice button clicked');
                this.toggleBrandVoiceDropdown();
            });
        }

        // Brand voice options
        document.querySelectorAll('.brand-voice-option').forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Brand voice option selected:', option.textContent.trim());
                this.selectBrandVoice(option.dataset.value, option.textContent.trim());
            });
        });

        // Mode buttons
        if (this.modeButtons) {
            this.modeButtons.forEach(btn => {
                btn.addEventListener('click', () => this.selectMode(btn));
            });
        }

        // More modes toggle
        if (this.moreModesBtn) {
            this.moreModesBtn.addEventListener('click', () => this.toggleMoreModes());
        }

        // Global click to close dropdown
        document.addEventListener('click', (e) => {
            if (this.brandVoiceDropdown && !this.brandVoiceDropdown.contains(e.target) && !this.brandVoiceBtn.contains(e.target)) {
                this.closeBrandVoiceDropdown();
            }
        });
    }

    autoResizeTextarea() {
        if (!this.chatInput) return;

        this.chatInput.style.height = 'auto';
        const scrollHeight = this.chatInput.scrollHeight;
        const maxHeight = 168; // Max height for ~7 lines

        if (scrollHeight > maxHeight) {
            this.chatInput.style.height = maxHeight + 'px';
            this.chatInput.style.overflowY = 'auto';
        } else {
            this.chatInput.style.height = Math.max(scrollHeight, 24) + 'px';
            this.chatInput.style.overflowY = 'hidden';
        }
    }

    startPlaceholderRotation() {
        if (this.placeholderInterval || !this.chatInput) return;

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
        if (this.brandVoiceDropdown) {
            const isCurrentlyShown = this.brandVoiceDropdown.classList.contains('show');
            
            // Close any other dropdowns first
            document.querySelectorAll('.brand-voice-dropdown.show').forEach(dropdown => {
                dropdown.classList.remove('show');
            });
            
            // Toggle this dropdown
            if (!isCurrentlyShown) {
                this.brandVoiceDropdown.classList.add('show');
                console.log('Brand voice dropdown shown');
            }
        }
    }

    closeBrandVoiceDropdown() {
        if (this.brandVoiceDropdown) {
            this.brandVoiceDropdown.classList.remove('show');
            console.log('Brand voice dropdown closed');
        }
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
                    <path d="M12 8l-6 6 1.41 1.41L12 10.83l4.59 4.58L18 14z"/>
                </svg>
                Less
            `;
        }
    }

    updateSendButton() {
        if (!this.chatInput || !this.sendBtn) return;

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
                brand_voice_id: this.isDemoMode ? null : (this.selectedBrandVoice || null),
                is_demo: this.isDemoMode
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

            // Add action buttons for AI responses (not for errors)
            if (!isError) {
                this.addActionButtons(bubbleDiv, content);
            }
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

    addActionButtons(bubbleDiv, content) {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';

        const copyBtn = document.createElement('button');
        copyBtn.className = 'action-btn copy-btn';
        copyBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
            </svg>
        `;
        copyBtn.title = 'Copy response';
        copyBtn.addEventListener('click', () => this.copyToClipboard(content));

        const regenerateBtn = document.createElement('button');
        regenerateBtn.className = 'action-btn regenerate-btn';
        regenerateBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
            </svg>
        `;
        regenerateBtn.title = 'Regenerate response';
        regenerateBtn.addEventListener('click', () => this.regenerateResponse());

        actionsDiv.appendChild(copyBtn);
        actionsDiv.appendChild(regenerateBtn);

        bubbleDiv.style.position = 'relative';
        bubbleDiv.appendChild(actionsDiv);
    }

    async copyToClipboard(content, button) {
        try {
            // Strip HTML tags for plain text copying
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = content;
            const plainText = tempDiv.textContent || tempDiv.innerText || '';

            await navigator.clipboard.writeText(plainText);

            // Show success feedback
            this.showCopyFeedback();
        } catch (err) {
            console.error('Failed to copy text: ', err);
            // Fallback for older browsers
            this.fallbackCopyToClipboard(content);
        }
    }

    fallbackCopyToClipboard(content) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = content;
        const plainText = tempDiv.textContent || tempDiv.innerText || '';

        const textArea = document.createElement('textarea');
        textArea.value = plainText;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            document.execCommand('copy');
            this.showCopyFeedback();
        } catch (err) {
            console.error('Fallback: Oops, unable to copy', err);
        }

        document.body.removeChild(textArea);
    }

    showCopyFeedback() {
        const feedback = document.createElement('div');
        feedback.innerHTML = `
            <div style="position: fixed; top: 20px; right: 20px; background: var(--clearwater-teal); color: var(--cloud-white); padding: 12px 20px; border-radius: 8px; font-size: 0.9rem; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <i class="fas fa-check" style="margin-right: 8px;"></i>
                Response copied to clipboard!
            </div>
        `;

        document.body.appendChild(feedback);

        setTimeout(() => {
            if (feedback.parentNode) {
                feedback.parentNode.removeChild(feedback);
            }
        }, 2000);
    }

    regenerateResponse() {
        if (this.isGenerating) {
            return;
        }

        // Get the last user message to regenerate response
        const messages = this.chatMessages.querySelectorAll('.message');
        let lastUserMessage = null;

        for (let i = messages.length - 1; i >= 0; i--) {
            if (messages[i].classList.contains('message-user')) {
                const bubble = messages[i].querySelector('.message-bubble');
                if (bubble) {
                    lastUserMessage = bubble.textContent;
                    break;
                }
            }
        }

        if (!lastUserMessage) {
            console.error('No user message found to regenerate response');
            return;
        }

        // Remove the last AI response
        const lastAiMessage = this.chatMessages.querySelector('.message-ai:last-child');
        if (lastAiMessage) {
            lastAiMessage.remove();
        }

        // Generate new response
        this.generateResponse(lastUserMessage);
    }

    async generateResponse(prompt) {
        this.isGenerating = true;
        this.updateSendButtonLoading(true);

        // Add loading message
        const loadingId = this.addLoadingMessage();

        try {
            const requestData = {
                prompt: prompt,
                content_mode: this.currentMode,
                brand_voice_id: this.isDemoMode ? null : (this.selectedBrandVoice || null),
                is_demo: this.isDemoMode
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
        this.updateSendButtonLoading(false);
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

    handleInitialPrompt() {
        // Check for demo prompt from homepage
        const demoPrompt = sessionStorage.getItem('demoPrompt');
        const demoMode = sessionStorage.getItem('demoMode');

        if (demoPrompt && this.chatInput) {
            // Clear the session storage
            sessionStorage.removeItem('demoPrompt');
            sessionStorage.removeItem('demoMode');

            // Set the prompt in the textarea
            this.chatInput.value = demoPrompt;
            this.autoResizeTextarea();
            this.updateSendButton();

            // Set the mode if available
            if (demoMode) {
                const modeButton = document.querySelector(`[data-mode="${demoMode}"]`);
                if (modeButton) {
                    this.selectMode(modeButton);
                }
            }

            // Auto-send the message after a brief delay
            setTimeout(() => {
                this.sendMessage();
            }, 500);
        }
    }

    setupDemoMode() {
        if (this.isDemoMode) {
            // Disable brand voice dropdown if it exists
            if (this.brandVoiceBtn) {
                this.brandVoiceBtn.style.cursor = 'not-allowed';
                this.brandVoiceBtn.style.opacity = '0.7';
            }

            // Disable attachment button
            const attachmentBtn = document.querySelector('.attachment-btn');
            if (attachmentBtn) {
                attachmentBtn.style.cursor = 'not-allowed';
                attachmentBtn.style.opacity = '0.6';
                attachmentBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.showPremiumMessage();
                });
            }

            // Update welcome screen message for demo users
            const welcomeScreen = document.querySelector('.welcome-screen');
            if (welcomeScreen && !this.isLoggedIn) {
                const heading = welcomeScreen.querySelector('h1');
                const paragraph = welcomeScreen.querySelector('p');

                if (heading) heading.textContent = 'Try GoldenDoodleLM';
                if (paragraph) paragraph.innerHTML = 'Experience trauma-informed AI communication. <a href="/register" class="text-primary">Sign up</a> for full features including brand voice and chat history.';
            }
        }
    }

    showPremiumMessage() {
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

    handleAttachment() {
        // Check if in demo mode
        if (this.isDemoMode) {
            this.showPremiumMessage();
            return;
        }

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
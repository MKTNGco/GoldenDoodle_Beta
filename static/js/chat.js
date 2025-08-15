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
        this.currentSessionId = null;
        this.isInitialized = false; // Prevent double initialization

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

        // Add global error handlers to prevent unhandled rejections
        this.setupGlobalErrorHandlers();

        // Only initialize if we're on the chat page and not already initialized
        if (this.initializeElements() && !this.isInitialized) {
            this.isInitialized = true;
            this.bindEvents();
            this.autoResizeTextarea();
            this.startPlaceholderRotation();
            this.updateSendButton();
            this.handleInitialPrompt();
            this.setupDemoMode();
            this.loadChatHistory();
        }
    }

    setupGlobalErrorHandlers() {
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            event.preventDefault(); // Prevent the default console error

            // Reset UI state if we're in a generating state
            if (this.isGenerating) {
                console.log('Resetting UI due to unhandled rejection');
                this.isGenerating = false;
                this.updateSendButton();
                this.updateSendButtonLoading(false);

                // Remove any loading messages
                const loadingMessages = document.querySelectorAll('[id^="loading-"]');
                loadingMessages.forEach(msg => msg.remove());

                // Show error message
                this.addMessage('Connection error occurred. Please try again.', 'ai', true);
            }
        });

        // Handle general errors
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);

            // Reset UI state if we're in a generating state
            if (this.isGenerating) {
                this.isGenerating = false;
                this.updateSendButton();
                this.updateSendButtonLoading(false);
            }
        });
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
        this.newChatBtn = document.getElementById('newChatBtn');

        // Check if we're on the chat page
        if (!this.chatInput || !this.sendBtn || !this.chatMessages) {
            console.log('Chat elements not found - not on chat page');
            return false;
        }
        return true;
    }

    bindEvents() {
        // Prevent double binding by removing existing listeners first
        this.unbindEvents();

        // Textarea events
        if (this.chatInput) {
            this.chatInput.addEventListener('input', this.handleInput.bind(this));
            this.chatInput.addEventListener('keydown', this.handleKeydown.bind(this));
            this.chatInput.addEventListener('focus', this.handleFocus.bind(this));
            this.chatInput.addEventListener('blur', this.handleBlur.bind(this));
        }

        // Send button
        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', this.handleSendClick.bind(this));
        }

        // Attachment button
        const attachmentBtn = document.querySelector('.attachment-btn');
        if (attachmentBtn) {
            attachmentBtn.addEventListener('click', this.handleAttachment.bind(this));
        }

        // Brand voice selector
        if (this.brandVoiceBtn) {
            this.brandVoiceBtn.addEventListener('click', this.handleBrandVoiceClick.bind(this));
        }

        // Brand voice options - use event delegation to prevent duplicates
        document.addEventListener('click', this.handleBrandVoiceOptionClick.bind(this));

        // Mode buttons
        if (this.modeButtons) {
            this.modeButtons.forEach(btn => {
                btn.addEventListener('click', () => this.selectMode(btn));
            });
        }

        // More modes toggle
        if (this.moreModesBtn) {
            this.moreModesBtn.addEventListener('click', this.toggleMoreModes.bind(this));
        }

        // New chat button
        if (this.newChatBtn) {
            this.newChatBtn.addEventListener('click', this.handleNewChatClick.bind(this));
        }

        // Global click to close dropdown
        document.addEventListener('click', this.handleGlobalClick.bind(this));
    }

    unbindEvents() {
        // Remove existing event listeners to prevent duplicates
        if (this.chatInput) {
            this.chatInput.removeEventListener('input', this.handleInput);
            this.chatInput.removeEventListener('keydown', this.handleKeydown);
            this.chatInput.removeEventListener('focus', this.handleFocus);
            this.chatInput.removeEventListener('blur', this.handleBlur);
        }

        if (this.sendBtn) {
            this.sendBtn.removeEventListener('click', this.handleSendClick);
        }

        if (this.brandVoiceBtn) {
            this.brandVoiceBtn.removeEventListener('click', this.handleBrandVoiceClick);
        }

        if (this.moreModesBtn) {
            this.moreModesBtn.removeEventListener('click', this.toggleMoreModes);
        }

        if (this.newChatBtn) {
            this.newChatBtn.removeEventListener('click', this.handleNewChatClick);
        }
    }

    // Event handler methods
    handleInput() {
        this.autoResizeTextarea();
        this.updateSendButton();
    }

    handleKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }

    handleFocus() {
        this.stopPlaceholderRotation();
    }

    handleBlur() {
        if (!this.chatInput.value.trim()) {
            this.startPlaceholderRotation();
        }
    }

    handleSendClick() {
        this.sendMessage();
    }

    handleBrandVoiceClick(e) {
        e.preventDefault();
        e.stopPropagation();
        this.toggleBrandVoiceDropdown();
    }

    handleBrandVoiceOptionClick(e) {
        const option = e.target.closest('.brand-voice-option');
        if (option) {
            e.preventDefault();
            e.stopPropagation();
            this.selectBrandVoice(option.dataset.value, option.textContent.trim());
        }
    }

    handleNewChatClick() {
        this.startNewChat();
    }

    handleGlobalClick(e) {
        if (this.brandVoiceDropdown && 
            !this.brandVoiceDropdown.contains(e.target) && 
            !this.brandVoiceBtn.contains(e.target)) {
            this.closeBrandVoiceDropdown();
        }
    }

    autoResizeTextarea() {
        if (!this.chatInput) return;

        this.chatInput.style.height = 'auto';
        const scrollHeight = this.chatInput.scrollHeight;
        const maxHeight = 168;

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

            document.querySelectorAll('.brand-voice-dropdown.show').forEach(dropdown => {
                dropdown.classList.remove('show');
            });

            if (!isCurrentlyShown) {
                const buttonRect = this.brandVoiceBtn.getBoundingClientRect();
                this.brandVoiceDropdown.style.right = (window.innerWidth - buttonRect.right) + 'px';
                this.brandVoiceDropdown.style.bottom = (window.innerHeight - buttonRect.top + 8) + 'px';
                this.brandVoiceDropdown.classList.add('show');
            }
        }
    }

    closeBrandVoiceDropdown() {
        if (this.brandVoiceDropdown) {
            this.brandVoiceDropdown.classList.remove('show');
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

        try {
            // If no current session and logged in, start a new one
            if (!this.currentSessionId && this.isLoggedIn) {
                await this.startNewChat(false);
            }

            // Validate session ID
            if (this.isLoggedIn && !this.currentSessionId) {
                console.error('No valid session ID for logged-in user!');
                await this.startNewChat(false);
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

            // Get conversation history for context
            const conversationHistory = this.getConversationHistory();

            const requestData = {
                prompt: prompt,
                conversation_history: conversationHistory,
                content_mode: this.currentMode,
                brand_voice_id: this.isDemoMode ? null : (this.selectedBrandVoice || null),
                is_demo: this.isDemoMode,
                session_id: this.currentSessionId
            };

            // Make the request with proper error handling
            const response = await this.makeRequest('/generate', requestData);

            this.removeLoadingMessage(loadingId);

            if (response && response.response) {
                this.addMessage(response.response, 'ai');

                // Update chat title in sidebar
                if (this.isLoggedIn && this.currentSessionId) {
                    this.updateChatTitleInSidebar(this.currentSessionId, prompt);
                }
            } else {
                this.addMessage(response?.error || 'Sorry, I encountered an error. Please try again.', 'ai', true);
            }

        } catch (error) {
            console.error('Error in sendMessage:', error);

            // Remove any loading messages
            const loadingMessages = document.querySelectorAll('[id^="loading-"]');
            loadingMessages.forEach(msg => msg.remove());

            this.addMessage('Connection error. Please try again.', 'ai', true);
        } finally {
            // Always reset UI state
            this.isGenerating = false;
            this.updateSendButton();
            this.updateSendButtonLoading(false);
            this.chatInput.focus();
        }
    }

    async makeRequest(url, data, maxRetries = 3) {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 45000);

                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data),
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const responseText = await response.text();
                return JSON.parse(responseText);

            } catch (error) {
                console.error(`Attempt ${attempt} failed:`, error);

                if (attempt === maxRetries) {
                    throw error;
                }

                // Wait before retrying
                await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
            }
        }
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
            if (!isError) {
                this.addActionButtons(bubbleDiv, content);
            }
        } else {
            bubbleDiv.textContent = content;
        }

        messageDiv.appendChild(bubbleDiv);

        let chatContent = this.chatMessages.querySelector('.chat-content');
        if (!chatContent) {
            chatContent = document.createElement('div');
            chatContent.className = 'chat-content';
            this.chatMessages.appendChild(chatContent);
        }

        const welcomeScreen = chatContent.querySelector('.welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.remove();
        }

        chatContent.appendChild(messageDiv);

        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 10);

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

    async copyToClipboard(content) {
        try {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = content;
            const plainText = tempDiv.textContent || tempDiv.innerText || '';

            await navigator.clipboard.writeText(plainText);
            this.showCopyFeedback();
        } catch (err) {
            console.error('Failed to copy text: ', err);
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

        const lastAiMessage = this.chatMessages.querySelector('.message-ai:last-child');
        if (lastAiMessage) {
            lastAiMessage.remove();
        }

        // Set the prompt and send message
        this.chatInput.value = lastUserMessage;
        this.sendMessage();
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
        if (!this.isLoggedIn) {
            return;
        }

        const demoPrompt = sessionStorage.getItem('demoPrompt');
        const demoMode = sessionStorage.getItem('demoMode');

        if (demoPrompt && this.chatInput) {
            sessionStorage.removeItem('demoPrompt');
            sessionStorage.removeItem('demoMode');

            this.chatInput.value = demoPrompt;
            this.autoResizeTextarea();
            this.updateSendButton();

            if (demoMode) {
                const modeButton = document.querySelector(`[data-mode="${demoMode}"]`);
                if (modeButton) {
                    this.selectMode(modeButton);
                }
            }

            setTimeout(() => {
                this.sendMessage();
            }, 500);
        }
    }

    setupDemoMode() {
        if (this.isDemoMode) {
            if (this.brandVoiceBtn) {
                this.brandVoiceBtn.style.cursor = 'not-allowed';
                this.brandVoiceBtn.style.opacity = '0.7';
            }

            const attachmentBtn = document.querySelector('.attachment-btn');
            if (attachmentBtn) {
                attachmentBtn.style.cursor = 'not-allowed';
                attachmentBtn.style.opacity = '0.6';
                attachmentBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.showPremiumMessage();
                });
            }

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

        setTimeout(() => {
            if (tooltip.parentNode) {
                tooltip.parentNode.removeChild(tooltip);
            }
        }, 3000);
    }

    handleAttachment() {
        if (this.isDemoMode) {
            this.showPremiumMessage();
            return;
        }

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
        if (file.size > 5 * 1024 * 1024) {
            alert('File size must be less than 5MB');
            return;
        }

        try {
            const text = await this.readFileAsText(file);
            const truncatedText = text.substring(0, 2000);

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

    async startNewChat(clearUI = true) {
        const previousSessionId = this.currentSessionId;
        this.currentSessionId = null;

        if (!this.isLoggedIn) {
            if (clearUI) {
                this.clearChatMessages();
                this.chatInput.value = '';
                this.autoResizeTextarea();
                this.updateSendButton();
                this.chatInput.focus();
            }
            return;
        }

        try {
            const response = await fetch('/new-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.currentSessionId = data.session_id;

            if (clearUI) {
                document.querySelectorAll('.chat-history-item').forEach(item => {
                    item.classList.remove('active');
                });

                this.clearChatMessages();
                this.chatInput.value = '';
                this.autoResizeTextarea();
                this.updateSendButton();
                this.chatInput.focus();
            }

            this.addChatToSidebar({
                id: this.currentSessionId,
                title: 'New Chat',
                message_count: 0,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
            });

            setTimeout(() => {
                const newChatItem = document.querySelector(`[data-session-id="${this.currentSessionId}"]`);
                if (newChatItem) {
                    newChatItem.classList.add('active');
                }
            }, 100);

        } catch (error) {
            console.error('Error starting new chat session:', error);
            this.currentSessionId = null;
            if (clearUI) {
                this.clearChatMessages();
                this.chatInput.value = '';
                this.autoResizeTextarea();
                this.updateSendButton();
                this.chatInput.focus();
            }
        }
    }

    clearChatMessages() {
        this.chatMessages.innerHTML = '';

        const chatContent = document.createElement('div');
        chatContent.className = 'chat-content';

        const welcomeScreen = document.createElement('div');
        welcomeScreen.className = 'welcome-screen';

        const welcomeContent = document.createElement('div');
        welcomeContent.className = 'welcome-content';
        welcomeContent.innerHTML = `
            <h1>Ready to create compassionate content?</h1>
            <p>Start a conversation with GoldenDoodleLM to generate trauma-informed, healing-centered communication.</p>
        `;

        welcomeScreen.appendChild(welcomeContent);
        chatContent.appendChild(welcomeScreen);
        this.chatMessages.appendChild(chatContent);
        this.chatMessages.scrollTop = 0;
    }

    addChatToSidebar(chat) {
        const chatHistory = document.getElementById('chatHistory');
        if (!chatHistory) return;

        if (!chat || !chat.id) {
            console.error('Invalid chat data provided to addChatToSidebar:', chat);
            return;
        }

        // Prevent duplicates
        const existingChat = document.querySelector(`[data-session-id="${chat.id}"]`);
        if (existingChat) {
            const titleElement = existingChat.querySelector('.chat-session-title');
            const metaElement = existingChat.querySelector('.chat-session-meta span:first-child');

            if (titleElement) titleElement.textContent = chat.title;
            if (metaElement) metaElement.textContent = `${chat.message_count || 0} messages`;
            return;
        }

        const chatElement = document.createElement('div');
        chatElement.className = 'chat-history-item';
        chatElement.dataset.sessionId = chat.id;

        chatElement.innerHTML = `
            <div class="chat-session-title">${chat.title}</div>
            <div class="chat-session-meta">
                <span>${chat.message_count || 0} messages</span>
                <span>${this.formatDate(chat.updated_at || chat.created_at)}</span>
            </div>
            <button class="delete-session-btn" onclick="event.stopPropagation(); chatInterface.deleteSession('${chat.id}')">
                ×
            </button>
        `;

        chatElement.addEventListener('click', () => {
            this.loadChat(chat.id);
        });

        chatHistory.prepend(chatElement);
    }

    async loadChatHistory() {
        if (!this.isLoggedIn) return;

        try {
            const response = await fetch('/chat-history');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const chats = await response.json();

            const chatHistory = document.getElementById('chatHistory');
            if (!chatHistory) return;

            // Clear existing chats to prevent duplicates
            chatHistory.innerHTML = '';
            chats.forEach(chat => {
                this.addChatToSidebar(chat);
            });

            if (chats.length > 0) {
                await this.loadChat(chats[0].id);
            } else {
                await this.startNewChat();
            }

        } catch (error) {
            console.error('Error loading chat history:', error);
            await this.startNewChat();
        }
    }

    async loadChat(sessionId) {
        if (this.currentSessionId === sessionId) return;

        try {
            const response = await fetch(`/chat/${sessionId}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const chatData = await response.json();

            this.currentSessionId = null;
            this.clearChatMessages();
            this.currentSessionId = sessionId;

            if (chatData.messages && chatData.messages.length > 0) {
                let chatContent = this.chatMessages.querySelector('.chat-content');
                const welcomeScreen = chatContent.querySelector('.welcome-screen');
                if (welcomeScreen) {
                    welcomeScreen.remove();
                }

                chatData.messages.forEach(msg => {
                    this.addMessage(msg.content, msg.sender);
                });

                setTimeout(() => {
                    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
                }, 100);
            }

            document.querySelectorAll('.chat-history-item').forEach(item => {
                item.classList.remove('active');
                if (item.dataset.sessionId === sessionId) {
                    item.classList.add('active');
                }
            });

        } catch (error) {
            console.error(`Error loading chat ${sessionId}:`, error);
            this.currentSessionId = null;
            this.clearChatMessages();
            await this.startNewChat();
        }
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays === 1) return 'Today';
        if (diffDays === 2) return 'Yesterday';
        if (diffDays <= 7) return `${diffDays} days ago`;
        return date.toLocaleDateString();
    }

    updateChatTitleInSidebar(sessionId, firstMessage) {
        const chatItem = document.querySelector(`[data-session-id="${sessionId}"]`);
        if (chatItem) {
            const titleElement = chatItem.querySelector('.chat-session-title');
            if (titleElement) {
                const title = firstMessage.length > 50 ? firstMessage.substring(0, 47) + '...' : firstMessage;
                titleElement.textContent = title;
            }

            const metaElement = chatItem.querySelector('.chat-session-meta span:first-child');
            if (metaElement) {
                const currentCount = parseInt(metaElement.textContent) || 0;
                metaElement.textContent = `${currentCount + 2} messages`;
            }
        }
    }

    getConversationHistory() {
        const messages = [];
        const messageElements = this.chatMessages.querySelectorAll('.message:not([id^="loading-"])');

        messageElements.forEach(messageEl => {
            const isUser = messageEl.classList.contains('message-user');
            const isAi = messageEl.classList.contains('message-ai');

            if (isUser || isAi) {
                const bubbleEl = messageEl.querySelector('.message-bubble');
                if (bubbleEl) {
                    let content;
                    if (isUser) {
                        content = bubbleEl.textContent.trim();
                    } else {
                        const actionsEl = bubbleEl.querySelector('.message-actions');
                        if (actionsEl) {
                            const tempDiv = bubbleEl.cloneNode(true);
                            const tempActions = tempDiv.querySelector('.message-actions');
                            if (tempActions) {
                                tempActions.remove();
                            }
                            content = tempDiv.textContent.trim();
                        } else {
                            content = bubbleEl.textContent.trim();
                        }
                    }

                    if (content && content !== 'Thinking...') {
                        messages.push({
                            role: isUser ? 'user' : 'assistant',
                            content: content
                        });
                    }
                }
            }
        });

        return messages;
    }

    async deleteSession(sessionId) {
        if (!confirm('Are you sure you want to delete this conversation?')) return;

        try {
            const response = await fetch(`/api/chat-sessions/${sessionId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                const sessionElement = document.querySelector(`[data-session-id="${sessionId}"]`);
                if (sessionElement) {
                    sessionElement.remove();
                }

                if (this.currentSessionId === sessionId) {
                    this.currentSessionId = null;
                    this.clearChatMessages();

                    const remainingSessions = document.querySelectorAll('.chat-history-item');
                    if (remainingSessions.length > 0) {
                        const firstSession = remainingSessions[0];
                        const firstSessionId = firstSession.dataset.sessionId;
                        await this.loadChat(firstSessionId);
                    } else {
                        await this.startNewChat();
                    }
                }
            } else {
                console.error('Failed to delete session');
            }
        } catch (error) {
            console.error('Error deleting session:', error);
        }
    }
}

// New chat functionality
function startNewChat() {
    if (chatInterface) {
        chatInterface.startNewChat(true);
    } else {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = `
            <div class="chat-content">
                <div class="welcome-screen">
                    <div class="welcome-content">
                        <h1>Ready to create compassionate content?</h1>
                        <p>Start a conversation with GoldenDoodleLM to generate trauma-informed, healing-centered communication.</p>
                    </div>
                </div>
            </div>
        `;

        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.focus();
        }
    }
}

// Global chat interface reference
let chatInterface;

// Initialize chat interface - prevent double initialization
document.addEventListener('DOMContentLoaded', function() {
    if (!chatInterface) {
        chatInterface = new ChatInterface();
    }
});
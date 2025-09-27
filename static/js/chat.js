// GoldenDoodleLM Modern Chat Interface
console.log('ChatInterface script loaded');

// Prevent duplicate class declaration
if (typeof ChatInterface !== 'undefined') {
    console.warn('ChatInterface already defined, skipping redefinition');
} else {

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
        
        // Store bound functions to prevent duplicate event listeners
        this.boundHandleBrandVoiceClick = this.handleBrandVoiceClick.bind(this);
        
        setTimeout(() => {
            this.checkLibraries();
        }, 1000);

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

        // Debug: Check if brand voice elements are found
        console.log('🔍 BRAND VOICE ELEMENT DEBUG:');
        console.log('  brandVoiceBtn found:', !!this.brandVoiceBtn);
        console.log('  brandVoiceDropdown found:', !!this.brandVoiceDropdown);
        console.log('  selectedVoiceNameElement found:', !!this.selectedVoiceNameElement);
        if (this.brandVoiceBtn) {
            console.log('  brandVoiceBtn element:', this.brandVoiceBtn);
        }
        if (this.brandVoiceDropdown) {
            console.log('  brandVoiceDropdown element:', this.brandVoiceDropdown);
        }

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
            console.log('🔍 BINDING BRAND VOICE CLICK EVENT');
            this.brandVoiceBtn.addEventListener('click', this.boundHandleBrandVoiceClick);
            console.log('🔍 BRAND VOICE CLICK EVENT BOUND');
        } else {
            console.log('🔍 ERROR: brandVoiceBtn not found for event binding');
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
            this.brandVoiceBtn.removeEventListener('click', this.boundHandleBrandVoiceClick);
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
        this.autoCloseSidebarOnMobile();
    }

    handleKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }

    handleFocus() {
        this.stopPlaceholderRotation();
        this.autoCloseSidebarOnMobile();
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
        console.log('🔍 BRAND VOICE CLICK DEBUG: Button clicked!');
        console.log('  brandVoiceBtn exists:', !!this.brandVoiceBtn);
        console.log('  brandVoiceDropdown exists:', !!this.brandVoiceDropdown);
        e.preventDefault();
        e.stopPropagation();
        this.toggleBrandVoiceDropdown();
    }

    toggleBrandVoiceDropdown() {
        console.log('🔍 BRAND VOICE DROPDOWN DEBUG: Toggle called');
        console.log('  brandVoiceDropdown exists:', !!this.brandVoiceDropdown);
        
        if (this.brandVoiceDropdown) {
            const isCurrentlyShown = this.brandVoiceDropdown.classList.contains('show');
            console.log('  Currently shown:', isCurrentlyShown);

            document.querySelectorAll('.brand-voice-dropdown.show').forEach(dropdown => {
                dropdown.classList.remove('show');
            });

            if (!isCurrentlyShown) {
                const buttonRect = this.brandVoiceBtn.getBoundingClientRect();
                // Simple positioning - just below the button
                this.brandVoiceDropdown.style.position = 'fixed';
                this.brandVoiceDropdown.style.left = '50px';  // Fixed position for testing
                this.brandVoiceDropdown.style.top = '200px';  // Fixed position for testing
                this.brandVoiceDropdown.style.right = 'auto';
                this.brandVoiceDropdown.style.bottom = 'auto';
                this.brandVoiceDropdown.style.zIndex = '999999';
                this.brandVoiceDropdown.style.backgroundColor = 'white';
                this.brandVoiceDropdown.style.border = '2px solid red'; // Visible border for testing
                this.brandVoiceDropdown.classList.add('show');
                console.log('  Dropdown should now be visible at FIXED position: 50px, 200px');
                console.log('  Button position:', buttonRect.left, buttonRect.bottom);
            } else {
                console.log('  Dropdown was already shown, hiding it');
            }
        } else {
            console.log('  ERROR: brandVoiceDropdown not found!');
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

    autoCloseSidebarOnMobile() {
        // Check if we're on a mobile device (screen width <= 768px)
        if (window.innerWidth <= 768) {
            const sidebar = document.querySelector('.sidebar');
            if (sidebar) {
                // Force remove hover state by temporarily adding a class that prevents hover
                sidebar.classList.add('force-closed');

                // Remove the class after a short delay to restore normal hover functionality
                setTimeout(() => {
                    sidebar.classList.remove('force-closed');
                }, 300);
            }
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
            console.error('❌ Generation error:', error);

            // Remove any loading messages first
            const loadingMessages = document.querySelectorAll('[id^="loading-"]');
            loadingMessages.forEach(msg => {
                try {
                    msg.remove();
                } catch (removeError) {
                    console.error('Error removing loading message:', removeError);
                }
            });

            // Get the actual error message from the error object
            let errorMessage = 'Connection error. Please try again.';

            if (error && error.message) {
                errorMessage = error.message;
            } else if (typeof error === 'string') {
                errorMessage = error;
            }

            try {
                this.addMessage(errorMessage, 'ai', true);
            } catch (addMessageError) {
                console.error('Error adding error message:', addMessageError);
                // Fallback to alert if we can't add the message to chat
                alert(errorMessage);
            }

            // Log additional error details for debugging
            if (error && error.stack) {
                console.error('Error stack:', error.stack);
            }
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

                let response;
                try {
                    response = await fetch(url, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(data),
                        signal: controller.signal
                    });
                } catch (fetchError) {
                    console.error('Fetch request failed:', fetchError);
                    throw new Error(`Network request failed: ${fetchError.message}`);
                }

                clearTimeout(timeoutId);

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    const errorMessage = errorData.error || `HTTP ${response.status}: ${response.statusText}`;
                    throw new Error(errorMessage);
                }

                let responseData;
                try {
                    responseData = await response.json();
                } catch (jsonError) {
                    console.error('Failed to parse JSON response:', jsonError);
                    throw new Error('Invalid response format from server');
                }

                return responseData;

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
            // Create a temporary div to extract clean text from HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = this.formatMessage(content);

            // Extract clean text, preserving line breaks
            let plainText = tempDiv.innerText || tempDiv.textContent || '';

            // Clean up any extra whitespace while preserving intentional formatting
            plainText = plainText.replace(/\n\s*\n\s*\n/g, '\n\n').trim();

            await navigator.clipboard.writeText(plainText);
            this.showCopyFeedback();
        } catch (err) {
            console.error('Failed to copy text: ', err);
            this.fallbackCopyToClipboard(content);
        }
    }

    fallbackCopyToClipboard(content) {
        // Create a temporary div to extract clean text from HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = this.formatMessage(content);

        // Extract clean text, preserving line breaks
        let plainText = tempDiv.innerText || tempDiv.textContent || '';
        plainText = plainText.replace(/\n\s*\n\s*\n/g, '\n\n').trim();

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
        fileInput.title = 'Supported formats: .txt, .md, .pdf, .doc, .docx (Note: .docx format is recommended for Word documents)';
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

        this.showFileProcessingIndicator(file.name);

        try {
            const text = await this.extractTextFromFile(file);
            const truncatedText = text.substring(0, 2000);

            const currentText = this.chatInput.value;
            const newText = currentText + (currentText ? '\n\n' : '') +
                           `[Attached file: ${file.name}]\n${truncatedText}${text.length > 2000 ? '\n...(truncated)' : ''}`;

            this.chatInput.value = newText;
            this.autoResizeTextarea();
            this.updateSendButton();
            this.chatInput.focus();

            // Show success indicator
            this.showFileSuccessIndicator(file.name);

        } catch (error) {
            console.error('Error reading file:', error);
            
            if (error.message.includes('Unsupported file type')) {
                alert(`Error: ${error.message}. Please use .txt, .md, .pdf, .doc, or .docx files.`);
            } else {
                alert('Error reading file. Please try again or use a different file.');
            }
        }
    }

    showFileProcessingIndicator(fileName) {
        const indicator = document.createElement('div');
        indicator.id = 'file-processing-indicator';
        indicator.innerHTML = `
            <div style="position: fixed; top: 20px; right: 20px; background: var(--charcoal); color: var(--cloud-white); padding: 12px 16px; border-radius: 8px; font-size: 0.9rem; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                <i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i>
                Processing ${fileName}...
            </div>
        `;
        document.body.appendChild(indicator);
    }

    updateFileProcessingIndicator(fileName, message) {
        const indicator = document.getElementById('file-processing-indicator');
        if (indicator) {
            indicator.innerHTML = `
                <div style="position: fixed; top: 20px; right: 20px; background: var(--charcoal); color: var(--cloud-white); padding: 12px 16px; border-radius: 8px; font-size: 0.9rem; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                    <i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i>
                    ${message}
                </div>
            `;
        }
    }

    showFileSuccessIndicator(fileName) {
        const processingIndicator = document.getElementById('file-processing-indicator');
        if (processingIndicator) {
            processingIndicator.remove();
        }

        const indicator = document.createElement('div');
        indicator.innerHTML = `
            <div style="position: fixed; top: 20px; right: 20px; background: var(--success-green); color: black; padding: 12px 16px; border-radius: 8px; font-size: 0.9rem; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                <i class="fas fa-check" style="margin-right: 8px;"></i>
                ${fileName} attached successfully!
            </div>
        `;
        document.body.appendChild(indicator);

        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        }, 3000);
    }

    checkLibraries() {
        
        if (typeof pdfjsLib === 'undefined') {
            console.warn('PDF.js library not loaded - PDF extraction will not work');
        }
        if (typeof mammoth === 'undefined') {
            console.warn('Mammoth library not loaded - Word extraction will not work');
        }
        console.log('=== END LIBRARY CHECK ===');
    }

    async loadPDFJS() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.min.js';
            script.onload = () => {
                console.log('PDF.js loaded dynamically');
                resolve();
            };
            script.onerror = () => {
                console.error('Failed to load PDF.js dynamically');
                reject(new Error('Failed to load PDF.js'));
            };
            document.head.appendChild(script);
        });
    }

    async loadMammoth() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/mammoth@1.6.0/mammoth.browser.min.js';
            script.onload = () => {
                console.log('Mammoth loaded dynamically');
                resolve();
            };
            script.onerror = () => {
                console.error('Failed to load Mammoth dynamically');
                reject(new Error('Failed to load Mammoth'));
            };
            document.head.appendChild(script);
        });
    }

    async extractTextFromFile(file) {
        const fileExtension = file.name.split('.').pop().toLowerCase();
        
        switch (fileExtension) {
            case 'txt':
            case 'md':
                console.log('Using readFileAsText for text file');
                return await this.readFileAsText(file);
            
            case 'pdf':
                console.log('Using extractTextFromPDF for PDF file');
                return await this.extractTextFromPDF(file);
            
            case 'doc':
            case 'docx':
                console.log('Using extractTextFromWord for Word file');
                return await this.extractTextFromWord(file);
            
            default:
                throw new Error(`Unsupported file type: ${fileExtension}. Supported types: .txt, .md, .pdf, .doc, .docx`);
        }
    }

    async extractTextFromPDF(file) {
        try {
            // Wait for PDF.js to load if it's not available yet
            let attempts = 0;
            while (typeof pdfjsLib === 'undefined' && attempts < 10) {
                await new Promise(resolve => setTimeout(resolve, 100));
                attempts++;
            }

            // Check if PDF.js is available
            if (typeof pdfjsLib === 'undefined') {
                
                // Try to load PDF.js dynamically
                try {
                    await this.loadPDFJS();
                    if (typeof pdfjsLib === 'undefined') {
                        throw new Error('Failed to load PDF.js library');
                    }
                } catch (loadError) {
                    console.error('Failed to load PDF.js:', loadError);
                    throw new Error('PDF.js library not available. Please refresh the page and try again.');
                }
            }

            if (pdfjsLib.GlobalWorkerOptions) {
                pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js';
            }

            const arrayBuffer = await file.arrayBuffer();
            
            this.updateFileProcessingIndicator(file.name, 'Loading PDF document...');
            const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            
            let fullText = '';
            
            for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
                this.updateFileProcessingIndicator(file.name, `Extracting text from page ${pageNum} of ${pdf.numPages}...`);
                
                const page = await pdf.getPage(pageNum);
                const textContent = await page.getTextContent();
                
                const pageText = textContent.items
                    .map(item => item.str)
                    .join(' ');
                
                fullText += pageText + '\n';
            }
            
            if (fullText.trim().length === 0) {
                return `[PDF file: ${file.name}]\n\nNote: This PDF appears to contain only images or non-extractable text. Please copy and paste the text content manually.`;
            }
            
            return fullText.trim();
            
        } catch (error) {
            console.error('PDF extraction error:', error);
            return `[PDF file: ${file.name}]\n\nError extracting text from PDF: ${error.message}. Please copy and paste the text content manually, or save the PDF as a text file and try again.`;
        }
    }

    async extractTextFromWord(file) {
        try {
            
            let attempts = 0;
            while (typeof mammoth === 'undefined' && attempts < 10) {
                await new Promise(resolve => setTimeout(resolve, 100));
                attempts++;
            }

            if (typeof mammoth === 'undefined') {
                console.error('Mammoth library not loaded after waiting');
                
                try {
                    await this.loadMammoth();
                    if (typeof mammoth === 'undefined') {
                        throw new Error('Failed to load Mammoth library');
                    }
                } catch (loadError) {
                    console.error('Failed to load Mammoth:', loadError);
                    throw new Error('Mammoth library not available. Please refresh the page and try again.');
                }
            }

            const arrayBuffer = await file.arrayBuffer();
            
            this.updateFileProcessingIndicator(file.name, 'Extracting text from Word document...');
            
            try {
                const result = await mammoth.extractRawText({ arrayBuffer: arrayBuffer });
                
                if (!result.value || result.value.trim().length === 0) {
                    return `[Word document: ${file.name}]\n\nNote: This document appears to contain only images or non-extractable content. Please copy and paste the text content manually.`;
                }
                
                let extractedText = result.value.trim();
                if (result.messages && result.messages.length > 0) {
                    const warnings = result.messages
                        .filter(msg => msg.type === 'warning')
                        .map(msg => msg.message)
                        .join(', ');
                    if (warnings) {
                        extractedText += `\n\n[Note: Some formatting may have been lost during extraction: ${warnings}]`;
                    }
                }
                
                return extractedText;
                
            } catch (mammothError) {
                console.log('Mammoth extraction failed:', mammothError.message);
                
                // Check if this is a binary .doc file that can't be processed
                if (mammothError.message.includes('unexpected signature') || 
                    mammothError.message.includes('zip file') || 
                    mammothError.message.includes('central directory') ||
                    mammothError.message.includes('Invalid data')) {
                    
                    // For "Invalid data" errors, try plain text fallback first
                    if (mammothError.message.includes('Invalid data')) {
                        console.log('Invalid data error detected, trying plain text fallback...');
                        this.updateFileProcessingIndicator(file.name, 'Trying alternative extraction method...');
                        
                        try {
                            const textContent = await this.readFileAsText(file);
                            const isReadableText = this.isReadableText(textContent);
                            
                            if (textContent && textContent.trim().length > 0 && isReadableText) {
                                return `[Word document: ${file.name}]\n\n${textContent}\n\nNote: Extracted using fallback method. Some formatting may be lost.`;
                            }
                        } catch (textError) {
                            console.log('Plain text fallback also failed for invalid data');
                        }
                    }
                    
                    // Don't try plain text fallback for other binary .doc files
                    throw new Error(`This .doc file appears to be in an older binary format that cannot be processed. Please convert it to .docx format or copy and paste the text content manually.`);
                }
                
                // For other errors, try plain text fallback only if it's likely to be a text-based file
                console.log('Trying plain text fallback...');
                this.updateFileProcessingIndicator(file.name, 'Trying alternative extraction method...');
                
                try {
                    const textContent = await this.readFileAsText(file);
                    
                    // Check if the content looks like readable text (not binary garbage)
                    const isReadableText = this.isReadableText(textContent);
                    
                    if (textContent && textContent.trim().length > 0 && isReadableText) {
                        return `[Word document: ${file.name}]\n\n${textContent}\n\nNote: Extracted using fallback method. Some formatting may be lost.`;
                    } else {
                        console.log('Plain text fallback produced unreadable content');
                    }
                } catch (textError) {
                    console.log('Plain text fallback also failed');
                }
                
                // Re-throw the original Mammoth error
                throw mammothError;
            }
            
        } catch (error) {
            console.error('Word extraction error:', error);
            
            if (error.message.includes('zip file') || error.message.includes('central directory') || error.message.includes('unexpected signature') || error.message.includes('binary format') || error.message.includes('Invalid data')) {
                return `[Word document: ${file.name}]\n\nThis document could not be processed by our text extraction system. This may be due to:\n1. The file being in an older binary format (.doc)\n2. The file being corrupted or damaged\n3. The file containing unsupported content\n\nPlease try:\n1. Opening the document in Microsoft Word and saving it as .docx format\n2. Copying and pasting the text content manually\n3. Converting the file using an online .doc to .docx converter\n\nNote: Modern .docx files work much better with our system.`;
            }
            
            return `[Word document: ${file.name}]\n\nError extracting text from Word document: ${error.message}. Please copy and paste the text content manually, or save the document as a text file and try again.`;
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

    isReadableText(text) {
        // Check if text contains too many non-printable characters
        const nonPrintableCount = (text.match(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]/g) || []).length;
        const totalLength = text.length;
        const nonPrintableRatio = nonPrintableCount / totalLength;
        
        // If more than 10% of characters are non-printable, it's likely binary data
        if (nonPrintableRatio > 0.1) {
            return false;
        }
        
        // Check for common binary file signatures
        const binarySignatures = [
            '\x00\x00\x00\x00', // Common in binary files
            'Root Entry', // OLE compound document
            '\xFF\xFF\xFF\xFF' // Another common binary pattern
        ];
        
        for (const signature of binarySignatures) {
            if (text.includes(signature)) {
                return false;
            }
        }
        
        return true;
    }

    formatMessage(content) {
        // Check if marked library is available
        if (typeof marked !== 'undefined') {
            // Configure marked for safe rendering
            marked.setOptions({
                breaks: true,
                gfm: true,
                sanitize: false,
                smartLists: true,
                smartypants: false
            });

            // Parse markdown to HTML
            return marked.parse(content);
        } else {
            // Fallback to basic formatting if marked isn't loaded
            const escapedContent = content
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#x27;');

            return escapedContent
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/\n\n/g, '</p><p>')
                .replace(/\n/g, '<br>')
                .replace(/^/, '<p>')
                .replace(/$/, '</p>')
                .replace(/<p><\/p>/g, '');
        }
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

        // Get user's first name if logged in
        const userName = window.currentUserFirstName || 'there';

        welcomeContent.innerHTML = `
            <h1><strong>Hello, ${userName}</strong></h1>
            <p style="color: var(--text-secondary);">What can we get started on together?</p>
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

        // Create elements safely using DOM methods instead of innerHTML
        const titleDiv = document.createElement('div');
        titleDiv.className = 'chat-session-title';
        titleDiv.textContent = chat.title; // Safe: textContent escapes HTML

        const metaDiv = document.createElement('div');
        metaDiv.className = 'chat-session-meta';

        const messageSpan = document.createElement('span');
        messageSpan.textContent = `${chat.message_count || 0} messages`;

        const dateSpan = document.createElement('span');
        dateSpan.textContent = this.formatDate(chat.updated_at || chat.created_at);

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-session-btn';
        deleteBtn.textContent = '×';
        // Safe: Use event listener instead of inline onclick
        deleteBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            this.deleteSession(chat.id); // chat.id is safely passed as parameter
        });

        metaDiv.appendChild(messageSpan);
        metaDiv.appendChild(dateSpan);

        chatElement.appendChild(titleDiv);
        chatElement.appendChild(metaDiv);
        chatElement.appendChild(deleteBtn);

        chatElement.addEventListener('click', () => {
            this.loadChat(chat.id);
        });

        chatHistory.appendChild(chatElement);
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
            
            // Sort chats by updated_at in descending order (most recent first)
            const sortedChats = chats.sort((a, b) => {
                const dateA = new Date(a.updated_at || a.created_at);
                const dateB = new Date(b.updated_at || b.created_at);
                return dateB - dateA; // Most recent first
            });
            
            sortedChats.forEach(chat => {
                this.addChatToSidebar(chat);
            });

            // Only clear the chat messages, don't create a new session automatically
            this.clearChatMessages();

        } catch (error) {
            console.error('Error loading chat history:', error);
            // Only clear messages on error, don't create new session
            this.clearChatMessages();
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
        const userName = window.currentUserFirstName || 'there';

        chatMessages.innerHTML = `
            <div class="chat-content">
                <div class="welcome-screen">
                    <div class="welcome-content">
                        <h1><strong>Hello, ${userName}</strong></h1>
                        <p style="color: var(--text-secondary);">What can we get started on together?</p>
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

// Initialize chat when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    try {
        const chat = new ChatInterface();
        window.chat = chat; // Make globally accessible for debugging

        // Additional global error handlers
        window.addEventListener('unhandledrejection', function(event) {
            console.error('Global unhandled promise rejection:', event.reason);
            event.preventDefault();

            // If the chat interface exists and is in a generating state, reset it
            if (window.chat && window.chat.isGenerating) {
                console.log('Resetting chat interface due to unhandled rejection');
                try {
                    window.chat.isGenerating = false;
                    window.chat.updateSendButton();
                    window.chat.updateSendButtonLoading(false);

                    // Remove any loading messages
                    const loadingMessages = document.querySelectorAll('[id^="loading-"]');
                    loadingMessages.forEach(msg => msg.remove());

                    // Add an error message
                    window.chat.addMessage('Connection interrupted. Please try again.', 'ai', true);
                } catch (resetError) {
                    console.error('Error during chat reset:', resetError);
                }
            }
        });

    } catch (initError) {
        console.error('Failed to initialize chat:', initError);
    }
});

// Ensure all promises are caught on window load as well
window.addEventListener('load', function() {
    console.log('Window loaded, chat interface should be ready');
});
}
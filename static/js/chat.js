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
        this.currentSessionId = null; // Added for chat history

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
            this.loadChatHistory(); // Load chat history on initialization
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
        this.newChatBtn = document.getElementById('newChatBtn'); // New chat button

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

        // New chat button event listener
        if (this.newChatBtn) {
            this.newChatBtn.addEventListener('click', () => this.startNewChat());
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
                // Position the dropdown relative to the button
                const buttonRect = this.brandVoiceBtn.getBoundingClientRect();
                this.brandVoiceDropdown.style.right = (window.innerWidth - buttonRect.right) + 'px';
                this.brandVoiceDropdown.style.bottom = (window.innerHeight - buttonRect.top + 8) + 'px';

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

        // If no current session and logged in, start a new one
        if (!this.currentSessionId && this.isLoggedIn) {
            await this.startNewChat(false); // Start new chat without clearing UI immediately
        }

        // CRITICAL: Validate session ID before proceeding
        console.log('Sending message to session:', this.currentSessionId);
        
        if (this.isLoggedIn && !this.currentSessionId) {
            console.error('No valid session ID for logged-in user!');
            // Force create a new session
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

        try {
            console.log('🚀 Starting sendMessage request process');
            
            // Get conversation history for context
            const conversationHistory = this.getConversationHistory();
            console.log('📚 Got conversation history, length:', conversationHistory.length);
            
            const requestData = {
                prompt: prompt,
                conversation_history: conversationHistory,
                content_mode: this.currentMode,
                brand_voice_id: this.isDemoMode ? null : (this.selectedBrandVoice || null),
                is_demo: this.isDemoMode,
                session_id: this.currentSessionId
            };

            console.log('📦 Request data prepared:', {
                promptLength: prompt.length,
                conversationHistoryLength: conversationHistory.length,
                contentMode: this.currentMode,
                brandVoiceId: requestData.brand_voice_id,
                isDemo: this.isDemoMode,
                sessionId: this.currentSessionId
            });

            // Pre-fetch validation
            if (!requestData.prompt || !requestData.prompt.trim()) {
                throw new Error('Empty prompt detected');
            }
            
            console.log('🌐 Making fetch request to /generate...');
            console.log('🔍 Request validation passed, proceeding with fetch');
            
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });
            console.log('🌐 Fetch request completed, status:', response.status);
            
            if (!response) {
                throw new Error('No response received from server');
            }

            console.log('📄 Parsing JSON response...');
            const data = await response.json();
            console.log('📄 JSON parsed successfully');
            
            this.removeLoadingMessage(loadingId);

            if (response.ok) {
                console.log('✅ Response successful, adding message');
                this.addMessage(data.response, 'ai');
                
                // Update chat title in sidebar if this is the first message
                if (this.isLoggedIn && this.currentSessionId) {
                    console.log('📝 Updating chat title in sidebar');
                    this.updateChatTitleInSidebar(this.currentSessionId, prompt);
                }
            } else {
                console.log('❌ Response not ok, status:', response.status, 'error:', data.error);
                this.addMessage(data.error || 'Sorry, I encountered an error. Please try again.', 'ai', true);
            }

        } catch (error) {
            console.error('❌ SENDMESSAGE ERROR CAUGHT:', error);
            console.error('Error type:', typeof error);
            console.error('Error constructor:', error.constructor.name);
            console.error('Error name:', error.name);
            console.error('Error message:', error.message);
            console.error('Error stack:', error.stack);
            console.error('Error toString:', error.toString());
            
            // Log additional context
            console.error('Context when error occurred:');
            console.error('- Current session ID:', this.currentSessionId);
            console.error('- Is demo mode:', this.isDemoMode);
            console.error('- Is generating:', this.isGenerating);
            console.error('- Is logged in:', this.isLoggedIn);
            
            this.removeLoadingMessage(loadingId);
            
            // More specific error messages based on error type
            let errorMessage = 'I apologize, but I encountered an unexpected error. Please try again.';
            
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                errorMessage = 'Network connection error. Please check your internet connection and try again.';
            } else if (error.name === 'SyntaxError') {
                errorMessage = 'Server response error. Please refresh the page and try again.';
            } else if (error.message && error.message.includes('JSON')) {
                errorMessage = 'Invalid server response. Please try again or refresh the page.';
            }
            
            this.addMessage(errorMessage, 'ai', true);
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

        // CRITICAL: Ensure we have the correct chat content container for THIS session
        let chatContent = this.chatMessages.querySelector('.chat-content');
        if (!chatContent) {
            console.error('No chat content container found when adding message');
            // Create fresh container if missing - this should not normally happen
            chatContent = document.createElement('div');
            chatContent.className = 'chat-content';
            this.chatMessages.appendChild(chatContent);
        }

        // Remove welcome screen if it exists (when adding real messages)
        const welcomeScreen = chatContent.querySelector('.welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.remove();
        }

        // Add the message to the current conversation ONLY
        // Verify we have a valid session before adding
        if (!this.currentSessionId && this.isLoggedIn) {
            console.warn('Adding message without valid session ID');
        }
        
        chatContent.appendChild(messageDiv);
        
        // Scroll to bottom smoothly
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
        console.log('🚀 STARTING generateResponse function with prompt:', prompt);
        
        try {
            this.isGenerating = true;
            this.updateSendButtonLoading(true);

            // Add loading message
            const loadingId = this.addLoadingMessage();
            console.log('📝 Loading message added with ID:', loadingId);

            try {
                // Get conversation history for context (excluding the last AI message that was removed)
                const conversationHistory = this.getConversationHistory();
                console.log('📚 Conversation history retrieved, length:', conversationHistory.length);
                
                const requestData = {
                    prompt: prompt,
                    conversation_history: conversationHistory,
                    content_mode: this.currentMode,
                    brand_voice_id: this.isDemoMode ? null : (this.selectedBrandVoice || null),
                    is_demo: this.isDemoMode,
                    session_id: this.currentSessionId
                };

                console.log('=== CHAT DEBUG: About to send request ===');
                console.log('Request URL:', '/generate');
                console.log('Request method:', 'POST');
                console.log('Request headers:', {'Content-Type': 'application/json'});
                console.log('Request data:', requestData);
                console.log('Request body size:', JSON.stringify(requestData).length, 'characters');
                console.log('Current session ID:', this.currentSessionId);
                console.log('Is demo mode:', this.isDemoMode);

                // Pre-fetch validation
                if (!requestData.prompt || !requestData.prompt.trim()) {
                    throw new Error('Empty prompt detected in generateResponse');
                }
                
                console.log('🌐 About to make fetch request...');
                console.log('🔍 Request validation passed, proceeding with fetch');
                
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestData)
                });
                console.log('🌐 Fetch request completed');
                
                if (!response) {
                    throw new Error('No response received from server');
                }

                console.log('=== CHAT DEBUG: Response received ===');
                console.log('Response status:', response.status);
                console.log('Response ok:', response.ok);
                console.log('Response headers:', Object.fromEntries(response.headers));

                console.log('📄 About to parse JSON response...');
                const data = await response.json();
                console.log('📄 JSON response parsed successfully');
                
                console.log('=== CHAT DEBUG: Response data ===');
                console.log('Response data:', data);
                console.log('Response data keys:', Object.keys(data));
                
                this.removeLoadingMessage(loadingId);

                if (response.ok) {
                    console.log('✅ Request successful, adding AI message');
                    this.addMessage(data.response, 'ai');
                } else {
                    console.log('❌ Request failed with status:', response.status);
                    this.addMessage(data.error || 'Sorry, I encountered an error. Please try again.', 'ai', true);
                }

            } catch (fetchError) {
                console.error('❌ FETCH/NETWORK ERROR:', fetchError);
                console.error('Error name:', fetchError.name);
                console.error('Error message:', fetchError.message);
                console.error('Error stack:', fetchError.stack);
                console.error('Error toString:', fetchError.toString());
                this.removeLoadingMessage(loadingId);
                
                // More specific error handling
                let errorMessage = 'Network error: Unable to connect to server. Please check your connection and try again.';
                
                if (fetchError.name === 'AbortError') {
                    errorMessage = 'Request was cancelled. Please try again.';
                } else if (fetchError.message && fetchError.message.includes('Failed to fetch')) {
                    errorMessage = 'Connection failed. Please check your internet connection and try again.';
                }
                
                this.addMessage(errorMessage, 'ai', true);
            }

        } catch (outerError) {
            console.error('❌ OUTER FUNCTION ERROR:', outerError);
            console.error('Outer error name:', outerError.name);
            console.error('Outer error message:', outerError.message);
            console.error('Outer error stack:', outerError.stack);
            this.addMessage('An unexpected error occurred. Please refresh the page and try again.', 'ai', true);
        } finally {
            // Reset UI in finally block to ensure it always happens
            console.log('🔄 Resetting UI state');
            this.isGenerating = false;
            this.updateSendButtonLoading(false);
        }
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
        // Only handle session storage if user is logged in
        // Demo users should experience the response on the homepage instead
        if (!this.isLoggedIn) {
            return;
        }

        // Check for demo prompt from homepage (only for logged-in users)
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

    // Chat History Functionality
    async startNewChat(clearUI = true) {
        console.log('Starting new chat, clearUI:', clearUI, 'isLoggedIn:', this.isLoggedIn);
        
        // CRITICAL: Always clear current session ID first to prevent message bleeding
        const previousSessionId = this.currentSessionId;
        this.currentSessionId = null;
        console.log('Cleared current session ID. Previous:', previousSessionId);
        
        if (!this.isLoggedIn) {
            // For demo users, just clear the UI completely
            if (clearUI) {
                this.clearChatMessages();
                this.chatInput.value = '';
                this.autoResizeTextarea();
                this.updateSendButton();
                this.chatInput.focus();
            }
            console.log('Demo mode - session cleared');
            return;
        }

        // Fetch a new session ID for logged-in users
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
            
            // Set the new session ID AFTER successful creation
            this.currentSessionId = data.session_id;
            console.log('New session created:', this.currentSessionId);

            // ALWAYS clear UI for new sessions to ensure isolation
            if (clearUI) {
                // Remove active state from ALL sessions FIRST
                document.querySelectorAll('.chat-history-item').forEach(item => {
                    item.classList.remove('active');
                });
                
                // Completely clear the chat area
                this.clearChatMessages();
                
                // Clear and reset input
                this.chatInput.value = '';
                this.autoResizeTextarea();
                this.updateSendButton();
                this.chatInput.focus();
            }

            // Add the new chat to sidebar and make it active
            this.addChatToSidebar({ 
                id: this.currentSessionId, 
                title: 'New Chat', 
                message_count: 0,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
            });
            
            // Make the new chat active in the sidebar
            setTimeout(() => {
                const newChatItem = document.querySelector(`[data-session-id="${this.currentSessionId}"]`);
                if (newChatItem) {
                    newChatItem.classList.add('active');
                    console.log('New chat item made active in sidebar');
                }
            }, 100);

        } catch (error) {
            console.error('Error starting new chat session:', error);
            // Reset session state on error
            this.currentSessionId = null;
            // Always clear UI on error for clean state
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
        // CRITICAL: Completely clear the entire chat messages container
        this.chatMessages.innerHTML = '';
        
        // Create a fresh chat-content container
        const chatContent = document.createElement('div');
        chatContent.className = 'chat-content';
        
        // Add clean welcome screen with proper structure
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
        
        // Append the fresh container
        this.chatMessages.appendChild(chatContent);
        
        // Force scroll to top
        this.chatMessages.scrollTop = 0;
    }

    addChatToSidebar(chat) {
        const chatHistory = document.getElementById('chatHistory');
        if (!chatHistory) return;

        // Validate chat data
        if (!chat || !chat.id) {
            console.error('Invalid chat data provided to addChatToSidebar:', chat);
            return;
        }

        // Check if this chat already exists in sidebar
        const existingChat = document.querySelector(`[data-session-id="${chat.id}"]`);
        if (existingChat) {
            // Update existing chat instead of creating duplicate
            const titleElement = existingChat.querySelector('.chat-session-title');
            const metaElement = existingChat.querySelector('.chat-session-meta span:first-child');
            
            if (titleElement) titleElement.textContent = chat.title;
            if (metaElement) metaElement.textContent = `${chat.message_count || 0} messages`;
            console.log('Updated existing chat in sidebar:', chat.id);
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

        // Add click listener to load chat with proper session isolation
        chatElement.addEventListener('click', () => {
            console.log('Clicking chat item, loading session:', chat.id);
            this.loadChat(chat.id);
        });

        // Prepend to the list of chats (newest first)
        chatHistory.prepend(chatElement);
        console.log('Added new chat to sidebar:', chat.id);
    }

    async loadChatHistory() {
        if (!this.isLoggedIn) return; // Don't load history for demo users

        try {
            const response = await fetch('/chat-history');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const chats = await response.json();

            const chatHistory = document.getElementById('chatHistory');
            if (!chatHistory) return;

            // Clear existing chats and add loaded ones
            chatHistory.innerHTML = '';
            chats.forEach(chat => {
                this.addChatToSidebar(chat);
            });

            // If there are chats, load the most recent one
            if (chats.length > 0) {
                await this.loadChat(chats[0].id); // Load the first chat in the history
            } else {
                // If no history, start a new chat
                await this.startNewChat();
            }

        } catch (error) {
            console.error('Error loading chat history:', error);
            // Fallback: start a new chat if history fails to load
            await this.startNewChat();
        }
    }

    async loadChat(sessionId) {
        if (this.currentSessionId === sessionId) return; // Already loaded

        try {
            const response = await fetch(`/chat/${sessionId}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const chatData = await response.json();

            // CRITICAL: Clear previous session FIRST, then set new one
            console.log('Loading chat - clearing previous session:', this.currentSessionId);
            this.currentSessionId = null;
            
            // COMPLETELY clear the chat area - no partial clearing
            this.clearChatMessages();
            
            // NOW set the new session ID
            this.currentSessionId = sessionId;
            console.log('Set currentSessionId to:', this.currentSessionId);

            // Add messages to the chat interface in order
            if (chatData.messages && chatData.messages.length > 0) {
                // Get the fresh chat-content container that was created in clearChatMessages
                let chatContent = this.chatMessages.querySelector('.chat-content');
                
                // Remove welcome screen since we have messages
                const welcomeScreen = chatContent.querySelector('.welcome-screen');
                if (welcomeScreen) {
                    welcomeScreen.remove();
                }
                
                chatData.messages.forEach(msg => {
                    this.addMessage(msg.content, msg.sender);
                });
                
                // Scroll to bottom after loading all messages
                setTimeout(() => {
                    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
                }, 100);
            } else {
                // If no messages, the welcome screen from clearChatMessages is kept
                console.log('No messages found for session:', sessionId);
            }

            // Update sidebar to highlight the current chat
            document.querySelectorAll('.chat-history-item').forEach(item => {
                item.classList.remove('active');
                if (item.dataset.sessionId === sessionId) {
                    item.classList.add('active');
                }
            });

            console.log('Successfully loaded chat:', sessionId, 'with', chatData.messages ? chatData.messages.length : 0, 'messages');

        } catch (error) {
            console.error(`Error loading chat ${sessionId}:`, error);
            // Reset session ID on error and clear UI
            this.currentSessionId = null;
            this.clearChatMessages();
            // If chat fails to load, start a new chat
            await this.startNewChat();
        }
    }

    // Helper to generate title for a chat session
    async generateChatTitle(sessionId) {
        try {
            const response = await fetch('/generate-title', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId })
            });
            const data = await response.json();
            return data.title;
        } catch (error) {
            console.error('Error generating chat title:', error);
            return 'New Chat'; // Fallback title
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
                // Generate a short title from the first message
                const title = firstMessage.length > 50 ? firstMessage.substring(0, 47) + '...' : firstMessage;
                titleElement.textContent = title;
            }
            
            // Update message count
            const metaElement = chatItem.querySelector('.chat-session-meta span:first-child');
            if (metaElement) {
                const currentCount = parseInt(metaElement.textContent) || 0;
                metaElement.textContent = `${currentCount + 2} messages`; // +2 for user message and AI response
            }
        }
    }

    getConversationHistory() {
        const messages = [];
        const messageElements = this.chatMessages.querySelectorAll('.message:not(#loading-*)');
        
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
                        // For AI messages, get text content without action buttons
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
                // Remove from sidebar
                const sessionElement = document.querySelector(`[data-session-id="${sessionId}"]`);
                if (sessionElement) {
                    sessionElement.remove();
                }

                // If this was the current session, clear everything and start fresh
                if (this.currentSessionId === sessionId) {
                    console.log('Deleted current session, starting fresh');
                    this.currentSessionId = null;
                    this.clearChatMessages();
                    
                    // Check if there are other sessions to load
                    const remainingSessions = document.querySelectorAll('.chat-history-item');
                    if (remainingSessions.length > 0) {
                        // Load the first remaining session
                        const firstSession = remainingSessions[0];
                        const firstSessionId = firstSession.dataset.sessionId;
                        await this.loadChat(firstSessionId);
                    } else {
                        // No sessions left, start a completely new one
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
        // Fallback if chatInterface not available
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
        
        // Focus on the input
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.focus();
        }
    }
}

// Global chat interface reference
let chatInterface;

// Initialize chat interface
document.addEventListener('DOMContentLoaded', function() {
    chatInterface = new ChatInterface();
});
// GoldenDoodleLM Brand Voice Wizard
class BrandVoiceWizard {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.isSubmitting = false;
        this.initializeElements();
        this.bindEvents();
        this.updateStepVisibility();
        this.updateNavigationButtons();
    }

    initializeElements() {
        this.form = document.getElementById('brandVoiceForm');
        this.steps = document.querySelectorAll('.wizard-step');
        this.prevBtn = document.getElementById('prevBtn');
        this.nextBtn = document.getElementById('nextBtn');
        this.submitBtn = document.getElementById('submitBtn');
        this.voiceNameInput = document.getElementById('voiceName');
        this.toneCards = document.querySelectorAll('.tone-card');
        this.styleCards = document.querySelectorAll('.style-card');
        this.selectedToneInput = document.getElementById('selectedTone');
        this.selectedStyleInput = document.getElementById('selectedStyle');
        this.audienceSelect = document.getElementById('audience');
        this.valuesCheckboxes = document.querySelectorAll('.values-container input[type="checkbox"]');
    }

    bindEvents() {
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));

        // Tone selection
        this.toneCards.forEach(card => {
            card.addEventListener('click', () => this.selectTone(card));
        });

        // Style selection
        this.styleCards.forEach(card => {
            card.addEventListener('click', () => this.selectStyle(card));
        });

        // Voice name input validation
        this.voiceNameInput.addEventListener('input', () => this.validateStep1());

        // Navigation buttons
        this.prevBtn.addEventListener('click', () => this.changeStep(-1));
        this.nextBtn.addEventListener('click', () => this.changeStep(1));

        // Values validation
        this.valuesCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => this.validateStep3());
        });
    }

    selectTone(selectedCard) {
        // Remove selection from all tone cards
        this.toneCards.forEach(card => card.classList.remove('selected'));
        
        // Add selection to clicked card
        selectedCard.classList.add('selected');
        
        // Update hidden input
        this.selectedToneInput.value = selectedCard.dataset.value;
        
        // Validate step
        this.validateStep2();
    }

    selectStyle(selectedCard) {
        // Remove selection from all style cards
        this.styleCards.forEach(card => card.classList.remove('selected'));
        
        // Add selection to clicked card
        selectedCard.classList.add('selected');
        
        // Update hidden input
        this.selectedStyleInput.value = selectedCard.dataset.value;
        
        // Validate step
        this.validateStep2();
    }

    changeStep(direction) {
        const newStep = this.currentStep + direction;
        
        if (newStep < 1 || newStep > this.totalSteps) {
            return;
        }

        // Validate current step before proceeding
        if (direction > 0 && !this.validateCurrentStep()) {
            return;
        }

        this.currentStep = newStep;
        this.updateStepVisibility();
        this.updateNavigationButtons();
        
        // Scroll to top of form
        this.form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    updateStepVisibility() {
        this.steps.forEach((step, index) => {
            if (index + 1 === this.currentStep) {
                step.style.display = 'block';
                step.classList.add('fade-in');
            } else {
                step.style.display = 'none';
                step.classList.remove('fade-in');
            }
        });
    }

    updateNavigationButtons() {
        // Previous button
        this.prevBtn.style.display = this.currentStep === 1 ? 'none' : 'inline-block';
        
        // Next/Submit buttons
        if (this.currentStep === this.totalSteps) {
            this.nextBtn.style.display = 'none';
            this.submitBtn.style.display = 'inline-block';
        } else {
            this.nextBtn.style.display = 'inline-block';
            this.submitBtn.style.display = 'none';
        }

        // Update next button state
        this.nextBtn.disabled = !this.validateCurrentStep();
    }

    validateCurrentStep() {
        switch (this.currentStep) {
            case 1:
                return this.validateStep1();
            case 2:
                return this.validateStep2();
            case 3:
                return this.validateStep3();
            case 4:
                return this.validateStep4();
            default:
                return true;
        }
    }

    validateStep1() {
        const isValid = this.voiceNameInput.value.trim().length > 0;
        this.updateValidationUI(this.voiceNameInput, isValid);
        return isValid;
    }

    validateStep2() {
        const hasTone = this.selectedToneInput.value.length > 0;
        const hasStyle = this.selectedStyleInput.value.length > 0;
        return hasTone && hasStyle;
    }

    validateStep3() {
        const hasAudience = this.audienceSelect.value.length > 0;
        const hasValues = Array.from(this.valuesCheckboxes).some(cb => cb.checked);
        return hasAudience && hasValues;
    }

    validateStep4() {
        const keyMessages = this.getKeyMessages();
        return keyMessages.length > 0;
    }

    updateValidationUI(element, isValid) {
        if (isValid) {
            element.classList.remove('is-invalid');
            element.classList.add('is-valid');
        } else {
            element.classList.remove('is-valid');
            element.classList.add('is-invalid');
        }
    }

    getKeyMessages() {
        const messageInputs = document.querySelectorAll('#keyMessagesContainer input[type="text"]');
        const messages = [];
        
        messageInputs.forEach(input => {
            const value = input.value.trim();
            if (value) {
                messages.push(value);
            }
        });
        
        return messages;
    }

    getTerminology() {
        const terminologyRows = document.querySelectorAll('#terminologyContainer .row');
        const terminology = {};
        
        terminologyRows.forEach(row => {
            const avoidInput = row.querySelector('.avoid-term');
            const preferInput = row.querySelector('.prefer-term');
            
            if (avoidInput && preferInput) {
                const avoid = avoidInput.value.trim();
                const prefer = preferInput.value.trim();
                
                if (avoid && prefer) {
                    terminology[avoid] = prefer;
                }
            }
        });
        
        return terminology;
    }

    getSelectedValues() {
        const selectedValues = [];
        
        this.valuesCheckboxes.forEach(checkbox => {
            if (checkbox.checked) {
                selectedValues.push(checkbox.value);
            }
        });
        
        return selectedValues;
    }

    async handleSubmit(event) {
        event.preventDefault();
        
        if (this.isSubmitting) {
            return;
        }

        // Final validation
        if (!this.validateCurrentStep()) {
            this.showAlert('Please complete all required fields.', 'danger');
            return;
        }

        this.isSubmitting = true;
        this.updateSubmitButton();

        try {
            // Collect form data
            const formData = {
                name: this.voiceNameInput.value.trim(),
                voice_type: this.form.voice_type.value,
                tone: this.selectedToneInput.value,
                style: this.selectedStyleInput.value,
                audience: this.audienceSelect.value,
                values: this.getSelectedValues(),
                key_messages: this.getKeyMessages(),
                terminology: this.getTerminology()
            };

            // Submit to backend
            const response = await fetch('/create-brand-voice', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (response.ok) {
                this.showAlert(result.message, 'success');
                
                // Redirect to brand voices page after a short delay
                setTimeout(() => {
                    window.location.href = '/brand-voices';
                }, 2000);
            } else {
                this.showAlert(result.error || 'An error occurred while creating the brand voice.', 'danger');
            }

        } catch (error) {
            console.error('Error creating brand voice:', error);
            this.showAlert('A network error occurred. Please check your connection and try again.', 'danger');
        }

        this.isSubmitting = false;
        this.updateSubmitButton();
    }

    updateSubmitButton() {
        if (this.isSubmitting) {
            this.submitBtn.disabled = true;
            this.submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Creating...';
        } else {
            this.submitBtn.disabled = false;
            this.submitBtn.innerHTML = '<i class="fas fa-save me-1"></i>Create Brand Voice';
        }
    }

    showAlert(message, type) {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.alert');
        existingAlerts.forEach(alert => alert.remove());

        // Create new alert
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-3`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Insert before form
        this.form.parentNode.insertBefore(alertDiv, this.form);

        // Scroll to alert
        alertDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Auto-dismiss success alerts
        if (type === 'success') {
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    }
}

// Key Messages Management
function addKeyMessage() {
    const container = document.getElementById('keyMessagesContainer');
    const newMessage = document.createElement('div');
    newMessage.className = 'input-group mb-2';
    newMessage.innerHTML = `
        <input type="text" class="form-control" placeholder="e.g., Healing is possible for everyone">
        <button class="btn btn-outline-danger" type="button" onclick="removeKeyMessage(this)">
            <i class="fas fa-times"></i>
        </button>
    `;
    container.appendChild(newMessage);
    
    // Focus on the new input
    newMessage.querySelector('input').focus();
}

function removeKeyMessage(button) {
    const container = document.getElementById('keyMessagesContainer');
    const messageGroups = container.querySelectorAll('.input-group');
    
    // Don't remove if it's the last one
    if (messageGroups.length > 1) {
        button.closest('.input-group').remove();
    } else {
        // Clear the input instead
        button.closest('.input-group').querySelector('input').value = '';
    }
}

// Terminology Management
function addTerminology() {
    const container = document.getElementById('terminologyContainer');
    const newTerminology = document.createElement('div');
    newTerminology.className = 'row mb-2';
    newTerminology.innerHTML = `
        <div class="col-5">
            <input type="text" class="form-control avoid-term" placeholder="Avoid this term">
        </div>
        <div class="col-2 text-center">
            <i class="fas fa-arrow-right text-muted mt-2"></i>
        </div>
        <div class="col-4">
            <input type="text" class="form-control prefer-term" placeholder="Use this instead">
        </div>
        <div class="col-1">
            <button class="btn btn-outline-danger btn-sm" type="button" onclick="removeTerminology(this)">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    container.appendChild(newTerminology);
    
    // Focus on the first input
    newTerminology.querySelector('.avoid-term').focus();
}

function removeTerminology(button) {
    const container = document.getElementById('terminologyContainer');
    const terminologyRows = container.querySelectorAll('.row');
    
    // Don't remove if it's the last one
    if (terminologyRows.length > 1) {
        button.closest('.row').remove();
    } else {
        // Clear the inputs instead
        const row = button.closest('.row');
        row.querySelector('.avoid-term').value = '';
        row.querySelector('.prefer-term').value = '';
    }
}

// Global functions for step navigation (called from template)
function changeStep(direction) {
    if (window.brandVoiceWizard) {
        window.brandVoiceWizard.changeStep(direction);
    }
}

// Initialize wizard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.brandVoiceWizard = new BrandVoiceWizard();
});

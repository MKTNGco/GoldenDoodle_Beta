// GoldenDoodleLM Brand Voice Wizard
class BrandVoiceWizard {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 6;
        this.isSubmitting = false;
        this.autoSaveTimeout = null;
        this.profileId = null;
        this.isEditing = false;
        this.initializeElements();
        this.bindEvents();
        this.updateStepVisibility();
        this.updateNavigationButtons();
        this.updateProgress();
        this.loadExistingData();
    }

    initializeElements() {
        this.form = document.getElementById('brandVoiceForm');
        this.steps = document.querySelectorAll('.wizard-step');
        this.prevBtn = document.getElementById('prevBtn');
        this.nextBtn = document.getElementById('nextBtn');
        this.submitBtn = document.getElementById('submitBtn');
        this.currentStepNumber = document.getElementById('currentStepNumber');
        this.wizardProgress = document.getElementById('wizardProgress');

        // Step 1 required fields
        this.companyNameInput = document.getElementById('companyName');
        this.companyUrlInput = document.getElementById('companyUrl');
        this.voiceShortNameInput = document.getElementById('voiceShortName');

        // All form inputs for auto-save
        this.allInputs = this.form.querySelectorAll('input, textarea, select');
    }

    bindEvents() {
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));

        // Submit button click handler (additional safety)
        if (this.submitBtn) {
            this.submitBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('Submit button clicked directly');
                this.handleSubmit(e);
            });
        }

        // Required field validation for step 1
        [this.companyNameInput, this.companyUrlInput, this.voiceShortNameInput].forEach(input => {
            if (input) {
                input.addEventListener('input', () => {
                    this.validateStep1();
                    this.updateNavigationButtons();
                });
                input.addEventListener('blur', () => {
                    this.validateStep1();
                    this.updateNavigationButtons();
                });
            }
        });

        // Navigation buttons
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', () => this.changeStep(-1));
        }
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => this.changeStep(1));
        }

        // Auto-save functionality
        this.allInputs.forEach(input => {
            input.addEventListener('input', () => this.scheduleAutoSave());
            input.addEventListener('change', () => this.scheduleAutoSave());
        });

        // Prevent form submission on Enter key (except for submit button)
        this.form.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.type !== 'submit') {
                e.preventDefault();
            }
        });
    }

    scheduleAutoSave() {
        // Clear existing timeout
        if (this.autoSaveTimeout) {
            clearTimeout(this.autoSaveTimeout);
        }

        // Schedule auto-save after 2 seconds of inactivity
        this.autoSaveTimeout = setTimeout(() => {
            this.autoSave();
        }, 2000);
    }

    async autoSave() {
        // Only auto-save if we have the required fields from step 1
        if (!this.validateStep1()) {
            return;
        }

        try {
            const formData = this.collectFormData();
            formData.auto_save = true;
            formData.profile_id = this.profileId;

            const response = await fetch('/auto-save-brand-voice', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                const result = await response.json();
                this.profileId = result.profile_id;

                // Show subtle save indicator
                this.showSaveIndicator('saved');
            }
        } catch (error) {
            console.error('Auto-save error:', error);
            this.showSaveIndicator('error');
        }
    }

    showSaveIndicator(status) {
        // Remove existing indicators
        const existingIndicator = document.querySelector('.save-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }

        // Create new indicator
        const indicator = document.createElement('div');
        indicator.className = 'save-indicator position-fixed top-0 end-0 m-3 p-2 rounded';

        if (status === 'saved') {
            indicator.className += ' bg-success text-white';
            indicator.innerHTML = '<i class="fas fa-check me-1"></i>Saved';
        } else {
            indicator.className += ' bg-warning text-dark';
            indicator.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Save Error';
        }

        indicator.style.zIndex = '9999';
        document.body.appendChild(indicator);

        // Remove after 3 seconds
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.remove();
            }
        }, 3000);
    }

    async loadExistingData() {
        // Check if we're editing an existing profile
        const urlParams = new URLSearchParams(window.location.search);
        const editProfileId = urlParams.get('edit');

        if (editProfileId) {
            try {
                const response = await fetch(`/get-brand-voice/${editProfileId}`);
                if (response.ok) {
                    const data = await response.json();
                    this.populateForm(data);
                    this.profileId = editProfileId;
                    this.isEditing = true;

                    // Update UI to show we're editing
                    const title = document.querySelector('.card-header h4');
                    if (title) {
                        title.innerHTML = '<i class="fas fa-edit me-2"></i>Brand Voice Wizard';
                        title.className = 'mb-0 text-white';
                    }

                    const submitBtn = document.getElementById('submitBtn');
                    if (submitBtn) {
                        submitBtn.innerHTML = '<i class="fas fa-save me-1"></i>Update Brand Voice';
                    }
                } else {
                    this.showAlert('Failed to load brand voice data. Redirecting...', 'danger');
                    setTimeout(() => {
                        window.location.href = '/brand-voices';
                    }, 2000);
                }
            } catch (error) {
                console.error('Error loading existing data:', error);
                this.showAlert('Error loading brand voice data. Please try again.', 'danger');
            }
        }
    }

    populateForm(data) {
        Object.keys(data).forEach(key => {
            const input = this.form.querySelector(`[name="${key}"]`);
            if (input) {
                if (input.type === 'radio') {
                    const radioInput = this.form.querySelector(`[name="${key}"][value="${data[key]}"]`);
                    if (radioInput) radioInput.checked = true;
                } else {
                    input.value = data[key] || '';
                }
            }
        });
    }

    changeStep(direction) {
        const newStep = this.currentStep + direction;

        if (newStep < 1 || newStep > this.totalSteps) {
            return;
        }

        // Validate current step before proceeding forward
        if (direction > 0 && !this.validateCurrentStep()) {
            // Show validation errors
            if (this.currentStep === 1) {
                this.showAlert('Please fill in all required fields (Company Name, Company URL, and Voice Short Name) to continue.', 'warning');
                // Force validation UI to show
                this.updateValidationUI(this.companyNameInput, this.companyNameInput.value.trim().length > 0);
                this.updateValidationUI(this.companyUrlInput, this.companyUrlInput.value.trim().length > 0);
                this.updateValidationUI(this.voiceShortNameInput, this.voiceShortNameInput.value.trim().length > 0);
            }
            return;
        }

        this.currentStep = newStep;
        this.updateStepVisibility();
        this.updateNavigationButtons();
        this.updateProgress();

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
        if (this.prevBtn) {
            this.prevBtn.style.display = this.currentStep === 1 ? 'none' : 'inline-block';
        }

        // Next/Submit buttons
        if (this.currentStep === this.totalSteps) {
            if (this.nextBtn) {
                this.nextBtn.style.display = 'none';
            }
            if (this.submitBtn) {
                this.submitBtn.style.display = 'inline-block';
                // Enable submit button if required fields are filled
                const requiredFieldsValid = this.validateRequiredFields();
                this.submitBtn.disabled = !requiredFieldsValid || this.isSubmitting;
                
                if (requiredFieldsValid && !this.isSubmitting) {
                    this.submitBtn.classList.remove('btn-outline-success');
                    this.submitBtn.classList.add('btn-success');
                } else {
                    this.submitBtn.classList.remove('btn-success');
                    this.submitBtn.classList.add('btn-outline-success');
                }
            }
        } else {
            if (this.nextBtn) {
                this.nextBtn.style.display = 'inline-block';
                
                // Update next button state based on current step validation
                const isValid = this.validateCurrentStep();
                this.nextBtn.disabled = !isValid;

                if (this.currentStep === 1) {
                    // Update button text based on validation
                    if (isValid) {
                        this.nextBtn.innerHTML = 'Next<i class="fas fa-arrow-right ms-1"></i>';
                        this.nextBtn.classList.remove('btn-outline-primary');
                        this.nextBtn.classList.add('btn-primary');
                    } else {
                        this.nextBtn.innerHTML = 'Complete Required Fields<i class="fas fa-arrow-right ms-1"></i>';
                        this.nextBtn.classList.remove('btn-primary');
                        this.nextBtn.classList.add('btn-outline-primary');
                    }
                }
            }
            if (this.submitBtn) {
                this.submitBtn.style.display = 'none';
            }
        }
    }

    updateProgress() {
        const progressPercent = (this.currentStep / this.totalSteps) * 100;
        this.wizardProgress.style.width = `${progressPercent}%`;
        this.currentStepNumber.textContent = this.currentStep;
    }

    validateCurrentStep() {
        switch (this.currentStep) {
            case 1:
                return this.validateStep1();
            default:
                return true; // All other steps are optional
        }
    }

    validateStep1() {
        const hasCompanyName = this.companyNameInput.value.trim().length > 0;
        const hasCompanyUrl = this.companyUrlInput.value.trim().length > 0;
        const hasVoiceShortName = this.voiceShortNameInput.value.trim().length > 0;

        // Only show validation UI if fields have been touched
        if (this.companyNameInput.value.length > 0) {
            this.updateValidationUI(this.companyNameInput, hasCompanyName);
        }
        if (this.companyUrlInput.value.length > 0) {
            this.updateValidationUI(this.companyUrlInput, hasCompanyUrl);
        }
        if (this.voiceShortNameInput.value.length > 0) {
            this.updateValidationUI(this.voiceShortNameInput, hasVoiceShortName);
        }

        return hasCompanyName && hasCompanyUrl && hasVoiceShortName;
    }

    updateValidationUI(element, isValid) {
        element.classList.remove('is-valid', 'is-invalid');
        if (isValid) {
            element.classList.add('is-valid');
        } else {
            element.classList.add('is-invalid');
        }
    }

    collectFormData() {
        const formData = {};

        // Get all form data
        const formDataObj = new FormData(this.form);
        for (let [key, value] of formDataObj.entries()) {
            formData[key] = value;
        }

        // Handle radio buttons that might not be selected
        const radioGroups = ['punctuation_contractions', 'punctuation_oxford_comma'];
        radioGroups.forEach(group => {
            const checkedRadio = this.form.querySelector(`input[name="${group}"]:checked`);
            if (checkedRadio) {
                formData[group] = checkedRadio.value === 'true';
            } else {
                formData[group] = null;
            }
        });

        return formData;
    }

    validateRequiredFields() {
        const hasCompanyName = this.companyNameInput && this.companyNameInput.value.trim().length > 0;
        const hasCompanyUrl = this.companyUrlInput && this.companyUrlInput.value.trim().length > 0;
        const hasVoiceShortName = this.voiceShortNameInput && this.voiceShortNameInput.value.trim().length > 0;
        
        return hasCompanyName && hasCompanyUrl && hasVoiceShortName;
    }

    async handleSubmit(event) {
        event.preventDefault();

        console.log('Submit button clicked, starting validation...');

        // Validate required fields
        if (!this.validateRequiredFields()) {
            console.log('Validation failed - missing required fields');
            this.showAlert('Please fill in all required fields (Company Name, Company URL, and Voice Short Name).', 'danger');
            this.currentStep = 1; // Go back to first step
            this.updateStepVisibility();
            this.updateNavigationButtons();
            this.updateProgress();
            return;
        }

        console.log('Validation passed, proceeding with submission...');

        // Prevent double submission
        if (this.isSubmitting) {
            console.log('Already submitting, ignoring duplicate submission');
            return;
        }

        this.isSubmitting = true;
        this.updateSubmitButton();

        // Show loading message
        this.showAlert('Creating your brand voice... This may take a moment.', 'info');

        try {
            const formData = this.collectFormData();
            
            // Don't set profile_id for creation, only for editing
            if (this.isEditing && this.profileId) {
                formData.brand_voice_id = this.profileId;
            }

            // Add voice_type explicitly
            formData.voice_type = 'company'; // Always create as company voice
            
            console.log('Submitting form data:', {
                company_name: formData.company_name,
                company_url: formData.company_url,
                voice_short_name: formData.voice_short_name,
                voice_type: formData.voice_type,
                is_editing: this.isEditing,
                profile_id: this.profileId
            }); // Debug log (limited to avoid logging sensitive data)

            const response = await fetch('/create-brand-voice', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            console.log('Response received:', response.status, response.statusText);

            if (!response.ok) {
                // Try to get error details from response
                let errorMessage = 'An error occurred while creating the brand voice.';
                try {
                    const errorResult = await response.json();
                    console.error('Server error response:', errorResult);
                    errorMessage = errorResult.error || errorMessage;
                } catch (parseError) {
                    console.error('Failed to parse error response:', parseError);
                    const responseText = await response.text();
                    console.error('Raw response text:', responseText);
                    errorMessage = `Server error (${response.status}): ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }

            const result = await response.json();
            console.log('Success result:', result);

            if (result.success) {
                this.showAlert(`✓ ${result.message}`, 'success');

                // Clear any auto-save data
                this.profileId = null;

                // Redirect to brand voices page after a short delay
                setTimeout(() => {
                    window.location.href = '/brand-voices';
                }, 2000);
            } else {
                this.showAlert(result.error || 'An unexpected error occurred.', 'danger');
            }

        } catch (error) {
            console.error('Error creating brand voice:', error);
            this.showAlert(error.message || 'A network error occurred. Please check your connection and try again.', 'danger');
        } finally {
            this.isSubmitting = false;
            this.updateSubmitButton();
        }
    }

    updateSubmitButton() {
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            if (this.isSubmitting) {
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Creating Brand Voice...';
                submitBtn.disabled = true;
                submitBtn.classList.add('btn-secondary');
                submitBtn.classList.remove('btn-success');
            } else {
                const isEditing = new URLSearchParams(window.location.search).get('edit');
                submitBtn.innerHTML = `<i class="fas fa-save me-1"></i>${isEditing ? 'Update' : 'Create'} Brand Voice`;
                submitBtn.disabled = false;
                submitBtn.classList.add('btn-success');
                submitBtn.classList.remove('btn-secondary');
            }
        }
    }

    showAlert(message, type) {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.alert');
        existingAlerts.forEach(alert => {
            if (!alert.classList.contains('alert-info')) { // Keep the info alert
                alert.remove();
            }
        });

        // Create new alert
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-3`;
        
        // Safely set the message content using textContent to prevent XSS
        const messageSpan = document.createElement('span');
        messageSpan.textContent = message;
        alertDiv.appendChild(messageSpan);
        
        // Add the close button safely
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('data-bs-dismiss', 'alert');
        alertDiv.appendChild(closeButton);

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

// Initialize wizard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.brandVoiceWizard = new BrandVoiceWizard();
});

// Add some CSS for the fade-in animation and save indicator
const style = document.createElement('style');
style.textContent = `
    .wizard-step {
        display: none;
    }

    .fade-in {
        animation: fadeIn 0.3s ease-in;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .slider-container {
        margin-bottom: 1rem;
    }

    .form-range {
        margin: 0.5rem 0;
    }

    .save-indicator {
        font-size: 0.875rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        animation: slideIn 0.3s ease-out;
    }

    @keyframes slideIn {
        from { transform: translateX(100%); }
        to { transform: translateX(0); }
    }
`;
document.head.appendChild(style);
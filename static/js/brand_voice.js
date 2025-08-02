
// GoldenDoodleLM Brand Voice Wizard
class BrandVoiceWizard {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 6;
        this.isSubmitting = false;
        this.autoSaveTimeout = null;
        this.profileId = null;
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

        // Required field validation for step 1
        [this.companyNameInput, this.companyUrlInput, this.voiceShortNameInput].forEach(input => {
            input.addEventListener('input', () => this.validateStep1());
        });

        // Navigation buttons
        this.prevBtn.addEventListener('click', () => this.changeStep(-1));
        this.nextBtn.addEventListener('click', () => this.changeStep(1));

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
                }
            } catch (error) {
                console.error('Error loading existing data:', error);
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

        // Validate current step before proceeding
        if (direction > 0 && !this.validateCurrentStep()) {
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
        
        // Update validation UI
        this.updateValidationUI(this.companyNameInput, hasCompanyName);
        this.updateValidationUI(this.companyUrlInput, hasCompanyUrl);
        this.updateValidationUI(this.voiceShortNameInput, hasVoiceShortName);
        
        return hasCompanyName && hasCompanyUrl && hasVoiceShortName;
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

    async handleSubmit(event) {
        event.preventDefault();
        
        if (this.isSubmitting) {
            return;
        }

        // Final validation
        if (!this.validateStep1()) {
            this.showAlert('Please complete all required fields in Step 1.', 'danger');
            this.currentStep = 1;
            this.updateStepVisibility();
            this.updateNavigationButtons();
            this.updateProgress();
            return;
        }

        this.isSubmitting = true;
        this.updateSubmitButton();

        try {
            const formData = this.collectFormData();
            formData.profile_id = this.profileId;

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
        existingAlerts.forEach(alert => {
            if (!alert.classList.contains('alert-info')) { // Keep the info alert
                alert.remove();
            }
        });

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

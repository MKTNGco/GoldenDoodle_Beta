
// GoldenDoodleLM Pricing Page
class PricingPage {
    constructor() {
        this.plans = [];
        this.isAnnual = false;
        this.initializeElements();
        this.bindEvents();
        this.loadPlans();
    }

    initializeElements() {
        this.pricingContainer = document.getElementById('pricingContainer');
        this.billingToggle = document.getElementById('billingToggle');
        this.featuresTableBody = document.getElementById('featuresTableBody');
        this.loadingIndicator = document.getElementById('loadingIndicator');
    }

    bindEvents() {
        if (this.billingToggle) {
            this.billingToggle.addEventListener('change', () => {
                this.isAnnual = this.billingToggle.checked;
                this.updatePricing();
            });
        }
    }

    async loadPlans() {
        try {
            this.showLoading(true);
            
            const response = await fetch('/api/get-plans');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Received data:', data);
            
            // Check if we received an error object instead of an array
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Check if we received an array of plans
            if (!Array.isArray(data)) {
                throw new Error('Invalid data format received from server');
            }
            
            this.plans = data;
            console.log('Loaded plans:', this.plans);
            
            if (this.plans.length === 0) {
                throw new Error('No pricing plans available');
            }
            
            this.renderPricingCards();
            this.renderFeaturesTable();
            this.showLoading(false);
            
        } catch (error) {
            console.error('Error loading plans:', error);
            this.showError(`Failed to load pricing information: ${error.message}. Please refresh the page.`);
            this.showLoading(false);
        }
    }

    showLoading(show) {
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = show ? 'block' : 'none';
        }
        if (this.pricingContainer) {
            this.pricingContainer.style.display = show ? 'none' : 'block';
        }
    }

    showError(message) {
        if (this.pricingContainer) {
            this.pricingContainer.innerHTML = `
                <div class="col-12 text-center">
                    <div class="alert alert-danger" role="alert">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        ${message}
                    </div>
                </div>
            `;
        }
    }

    renderPricingCards() {
        if (!this.pricingContainer || !this.plans.length) return;

        const planOrder = ['free', 'solo', 'team', 'professional'];
        const sortedPlans = planOrder.map(id => this.plans.find(plan => plan.plan_id === id)).filter(Boolean);

        this.pricingContainer.innerHTML = sortedPlans.map(plan => this.createPricingCard(plan)).join('');
    }

    createPricingCard(plan) {
        // Add defensive checks for plan data
        if (!plan || typeof plan !== 'object') {
            console.error('Invalid plan data:', plan);
            return '';
        }
        
        const isPopular = plan.plan_id === 'team';
        const isFree = plan.plan_id === 'free';
        
        // Get pricing based on billing toggle
        let price, pricePeriod;
        if (isFree) {
            price = '$0';
            pricePeriod = '';
        } else if (this.isAnnual && plan.price_annual) {
            if (plan.plan_id === 'team') {
                price = `$${plan.price_annual}`;
                pricePeriod = '/user/month';
            } else {
                price = `$${plan.price_annual}`;
                pricePeriod = '/year';
            }
        } else {
            if (plan.plan_id === 'team') {
                price = `$${plan.price_monthly || '0'}`;
                pricePeriod = '/user/month';
            } else {
                price = `$${plan.price_monthly || '0'}`;
                pricePeriod = '/month';
            }
        }

        // Determine restricted features for free plan
        const restrictedFeatures = isFree ? ['Analysis & Brainstorm', 'Summarize'] : [];

        return `
            <div class="col-lg-3 col-md-6">
                <div class="card pricing-card h-100 ${isPopular ? 'popular-plan' : ''} ${isFree ? 'free-plan' : ''}">
                    ${isPopular ? '<div class="popular-badge">Most Popular</div>' : ''}
                    
                    <div class="card-header text-center">
                        <h3 class="plan-name">${plan.name || 'Unknown Plan'}</h3>
                        <p class="plan-description text-muted">${plan.target_user || 'No description available'}</p>
                    </div>
                    
                    <div class="card-body">
                        <div class="pricing-display text-center mb-4">
                            <div class="price-amount">${price}</div>
                            <div class="price-period">${pricePeriod}</div>
                            ${this.isAnnual && !isFree ? '<div class="savings-badge">Save 15%</div>' : ''}
                        </div>
                        
                        <div class="core-value mb-4">
                            <h6 class="fw-bold">Core Value:</h6>
                            <p class="text-muted small">${plan.core_value || 'No core value specified'}</p>
                        </div>
                        
                        <ul class="feature-list">
                            ${this.createFeatureList(plan, restrictedFeatures)}
                        </ul>
                    </div>
                    
                    <div class="card-footer text-center">
                        <a href="${isFree ? '/register' : '/register'}" class="btn ${isPopular ? 'btn-primary' : 'btn-outline-primary'} btn-lg w-100">
                            ${isFree ? 'Get Started Free' : 'Choose Plan'}
                        </a>
                    </div>
                </div>
            </div>
        `;
    }

    createFeatureList(plan, restrictedFeatures = []) {
        // Ensure restrictedFeatures is always an array
        const restrictedArray = Array.isArray(restrictedFeatures) ? restrictedFeatures : [];
        
        const features = [
            {
                name: 'Writing Tools',
                value: plan.templates === 'basic' ? 'Email, Social, Rewrite, Article' : 'All 7 Writing Tools',
                restricted: plan.templates === 'basic'
            },
            {
                name: 'Analysis & Brainstorm',
                value: plan.analysis_brainstorm ? 'Included' : 'Not Available',
                available: plan.analysis_brainstorm,
                restricted: !plan.analysis_brainstorm
            },
            {
                name: 'Monthly Tokens',
                value: plan.token_limit ? plan.token_limit.toLocaleString() : '0',
                available: true
            },
            {
                name: 'Brand Voices',
                value: plan.brand_voices === 0 ? 'None' : plan.brand_voices,
                available: plan.brand_voices > 0
            },
            {
                name: 'Chat History',
                value: plan.chat_history_limit === -1 ? 'Unlimited' : plan.chat_history_limit + ' chats',
                available: true
            },
            {
                name: 'User Seats',
                value: plan.user_seats + (plan.user_seats === 1 ? ' user' : ' users'),
                available: true
            },
            {
                name: 'Support Level',
                value: this.formatSupportLevel(plan.support_level),
                available: plan.support_level !== 'none'
            }
        ];

        return features.map(feature => {
            const isRestricted = restrictedArray.includes(feature.name) || feature.restricted;
            const isAvailable = feature.available !== false;
            
            return `
                <li class="feature-item ${!isAvailable ? 'unavailable' : ''}">
                    <i class="fas ${isAvailable ? 'fa-check' : 'fa-times'} feature-icon"></i>
                    <span class="feature-text ${isRestricted ? 'restricted' : ''}">${feature.value}</span>
                    ${isRestricted ? '<span class="restriction-note"> (Limited)</span>' : ''}
                </li>
            `;
        }).join('');
    }

    formatSupportLevel(level) {
        const levels = {
            'none': 'No Support',
            'email': 'Email Support',
            'priority': 'Priority Support',
            'top_priority': 'Premium Support'
        };
        return levels[level] || level;
    }

    renderFeaturesTable() {
        if (!this.featuresTableBody || !this.plans.length) return;

        const planOrder = ['free', 'solo', 'team', 'professional'];
        const sortedPlans = planOrder.map(id => this.plans.find(plan => plan.plan_id === id)).filter(Boolean);

        const features = [
            { name: 'Email Writing', key: 'templates', formatter: (plan) => plan.templates === 'basic' ? '✓ Basic' : '✓ Advanced' },
            { name: 'Article Writing', key: 'templates', formatter: (plan) => plan.templates === 'basic' ? '✓ Basic' : '✓ Advanced' },
            { name: 'Social Media', key: 'templates', formatter: (plan) => plan.templates === 'basic' ? '✓ Basic' : '✓ Advanced' },
            { name: 'Rewrite Tool', key: 'templates', formatter: (plan) => plan.templates === 'basic' ? '✓ Basic' : '✓ Advanced' },
            { name: 'Summarize', key: 'analysis_brainstorm', formatter: (plan) => plan.plan_id === 'free' ? '✗ Not Available' : '✓ Available' },
            { name: 'Brainstorm', key: 'analysis_brainstorm', formatter: (plan) => plan.plan_id === 'free' ? '✗ Not Available' : '✓ Available' },
            { name: 'Analysis', key: 'analysis_brainstorm', formatter: (plan) => plan.plan_id === 'free' ? '✗ Not Available' : '✓ Available' },
            { name: 'Monthly Tokens', key: 'token_limit', formatter: (plan) => plan.token_limit.toLocaleString() },
            { name: 'Brand Voices', key: 'brand_voices', formatter: (plan) => plan.brand_voices === 0 ? 'None' : plan.brand_voices },
            { name: 'Chat History', key: 'chat_history_limit', formatter: (plan) => plan.chat_history_limit === -1 ? 'Unlimited' : plan.chat_history_limit + ' chats' },
            { name: 'Team Seats', key: 'user_seats', formatter: (plan) => plan.user_seats + (plan.user_seats === 1 ? ' user' : ' users') },
            { name: 'Admin Controls', key: 'admin_controls', formatter: (plan) => plan.admin_controls ? '✓ Yes' : '✗ No' },
            { name: 'Support', key: 'support_level', formatter: (plan) => this.formatSupportLevel(plan.support_level) }
        ];

        this.featuresTableBody.innerHTML = features.map(feature => {
            const cells = sortedPlans.map(plan => {
                const value = feature.formatter(plan);
                const isUnavailable = value.includes('✗');
                return `<td class="text-center ${isUnavailable ? 'text-muted' : ''}">${value}</td>`;
            }).join('');
            
            return `<tr><td class="fw-semibold">${feature.name}</td>${cells}</tr>`;
        }).join('');
    }

    updatePricing() {
        this.renderPricingCards();
    }
}

// Initialize pricing page
document.addEventListener('DOMContentLoaded', function() {
    new PricingPage();
});

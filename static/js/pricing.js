
// GoldenDoodleLM Pricing Page
class PricingPage {
    constructor() {
        this.plans = [];
        this.isAnnual = false;
        this.showingTeamPlans = false;
        this.loadingPlans = false;
        this.initializeElements();
        this.bindEvents();
        this.loadPlans();
    }

    initializeElements() {
        this.individualPricingContainer = document.getElementById('individualPricingContainer');
        this.teamPricingContainer = document.getElementById('teamPricingContainer');
        this.individualPlansSection = document.getElementById('individualPlans');
        this.teamPlansSection = document.getElementById('teamPlans');
        this.billingToggle = document.getElementById('billingToggle');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.individualTypeRadio = document.getElementById('individualType');
        this.teamTypeRadio = document.getElementById('teamType');
    }

    bindEvents() {
        if (this.billingToggle) {
            this.billingToggle.addEventListener('change', () => {
                this.isAnnual = this.billingToggle.checked;
                this.updatePricing();
            });
        }

        if (this.individualTypeRadio) {
            this.individualTypeRadio.addEventListener('change', () => {
                if (this.individualTypeRadio.checked) {
                    this.showingTeamPlans = false;
                    this.switchPlanView();
                }
            });
        }

        if (this.teamTypeRadio) {
            this.teamTypeRadio.addEventListener('change', () => {
                if (this.teamTypeRadio.checked) {
                    this.showingTeamPlans = true;
                    this.switchPlanView();
                }
            });
        }
    }

    switchPlanView() {
        if (this.showingTeamPlans) {
            this.individualPlansSection.style.display = 'none';
            this.teamPlansSection.style.display = 'block';
        } else {
            this.individualPlansSection.style.display = 'block';
            this.teamPlansSection.style.display = 'none';
        }
        this.updatePricing();
    }

    async loadPlans() {
        if (this.loadingPlans) {
            return;
        }
        
        try {
            this.loadingPlans = true;
            this.showLoading(true);
            
            const response = await fetch('/api/get-plans');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Received data:', data);
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            if (!Array.isArray(data)) {
                throw new Error('Invalid data format received from server');
            }
            
            this.plans = data;
            console.log('Loaded plans:', this.plans);
            
            if (this.plans.length === 0) {
                throw new Error('No pricing plans available');
            }
            
            this.renderPricingCards();
            this.showLoading(false);
            
        } catch (error) {
            console.error('Error loading plans:', error);
            this.showError(`Failed to load pricing information: ${error.message}. Please refresh the page.`);
            this.showLoading(false);
        } finally {
            this.loadingPlans = false;
        }
    }

    showLoading(show) {
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = show ? 'block' : 'none';
        }
        if (this.individualPricingContainer) {
            this.individualPricingContainer.style.display = show ? 'none' : 'flex';
        }
        if (this.teamPricingContainer) {
            this.teamPricingContainer.style.display = show ? 'none' : 'flex';
        }
    }

    showError(message) {
        const errorHtml = `
            <div class="col-12 text-center">
                <div class="alert alert-danger" role="alert">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </div>
            </div>
        `;
        
        if (this.individualPricingContainer) {
            this.individualPricingContainer.innerHTML = errorHtml;
        }
        if (this.teamPricingContainer) {
            this.teamPricingContainer.innerHTML = errorHtml;
        }
    }

    renderPricingCards() {
        if (!this.plans.length) return;

        // Individual plans: free, solo, and professional
        const individualPlans = this.plans.filter(plan => ['free', 'solo', 'professional'].includes(plan.plan_id));
        if (this.individualPricingContainer && individualPlans.length) {
            this.individualPricingContainer.innerHTML = individualPlans.map(plan => this.createPricingCard(plan)).join('');
        }

        // Team plans: team only
        const teamPlans = this.plans.filter(plan => ['team'].includes(plan.plan_id));
        if (this.teamPricingContainer && teamPlans.length) {
            this.teamPricingContainer.innerHTML = teamPlans.map(plan => this.createPricingCard(plan)).join('');
        }
    }

    createPricingCard(plan) {
        if (!plan || typeof plan !== 'object') {
            console.error('Invalid plan data:', plan);
            return '';
        }
        
        const isPopular = plan.plan_id === 'solo' || (plan.plan_id === 'team' && this.showingTeamPlans);
        const isFree = plan.plan_id === 'free';
        
        // Get pricing based on billing toggle
        let price, pricePeriod;
        if (isFree) {
            price = '$0';
            pricePeriod = 'Forever free';
        } else if (this.isAnnual && plan.price_annual) {
            if (plan.plan_id === 'team') {
                price = `$${Math.round(plan.price_annual * 12 / 12)}`;
                pricePeriod = '/user/month (billed annually)';
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

        const features = this.getPlanFeatures(plan);

        return `
            <div class="col-lg-4 col-md-6 col-sm-8">
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
                            <h6 class="fw-bold text-primary">Core Value:</h6>
                            <p class="text-muted small">${plan.core_value || 'No core value specified'}</p>
                        </div>
                        
                        <ul class="feature-list">
                            ${features.map(feature => `
                                <li class="feature-item ${!feature.available ? 'unavailable' : ''}">
                                    <i class="fas ${feature.available ? 'fa-check' : 'fa-times'} feature-icon"></i>
                                    <span class="feature-text">${feature.text}</span>
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                    
                    <div class="card-footer text-center">
                        <a href="/register" class="btn ${isPopular ? 'btn-primary' : 'btn-outline-primary'} btn-lg w-100">
                            ${isFree ? 'Get Started Free' : 'Choose Plan'}
                        </a>
                    </div>
                </div>
            </div>
        `;
    }

    getPlanFeatures(plan) {
        const features = [];
        
        // Writing tools
        if (plan.templates === 'basic') {
            features.push({ text: 'Basic Writing Tools (Email, Social, Rewrite, Article)', available: true });
        } else {
            features.push({ text: 'All 7 Advanced Writing Tools', available: true });
        }
        
        // Analysis & Brainstorm
        features.push({ 
            text: 'Analysis & Brainstorm Tools', 
            available: plan.analysis_brainstorm 
        });
        
        // Monthly tokens
        features.push({ 
            text: `${plan.token_limit ? plan.token_limit.toLocaleString() : '0'} Monthly Tokens`, 
            available: true 
        });
        
        // Brand voices
        if (plan.brand_voices > 0) {
            features.push({ 
                text: `${plan.brand_voices} Brand Voice${plan.brand_voices > 1 ? 's' : ''}`, 
                available: true 
            });
        } else {
            features.push({ text: 'Brand Voices', available: false });
        }
        
        // Chat history
        if (plan.chat_history_limit === -1) {
            features.push({ text: 'Unlimited Chat History', available: true });
        } else {
            features.push({ text: `${plan.chat_history_limit} Saved Chats`, available: true });
        }
        
        // User seats (for team plans)
        if (plan.plan_id === 'team' || plan.plan_id === 'professional') {
            if (plan.plan_id === 'team') {
                features.push({ text: 'Minimum 3 User Seats', available: true });
            } else {
                features.push({ text: 'Unlimited User Seats', available: true });
            }
            
            // Admin controls for team plans
            if (plan.admin_controls) {
                features.push({ text: 'Admin Controls & User Management', available: true });
            }
        }
        
        // Support
        const supportLevels = {
            'none': 'Community Support',
            'email': 'Email Support',
            'priority': 'Priority Support',
            'top_priority': 'Premium Support'
        };
        
        features.push({ 
            text: supportLevels[plan.support_level] || 'Support', 
            available: plan.support_level !== 'none' 
        });
        
        return features;
    }

    updatePricing() {
        this.renderPricingCards();
    }
}

// Initialize pricing page
document.addEventListener('DOMContentLoaded', function() {
    new PricingPage();
});

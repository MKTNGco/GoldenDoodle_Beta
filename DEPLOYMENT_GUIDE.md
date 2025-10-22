# Flask Application - Deployment Guide

## Application Overview
Your Python Flask application is fully configured and ready for deployment with:
- **Database**: Neon PostgreSQL (configured in .env)
- **Web Server**: Gunicorn with gevent workers
- **Health Check**: Available at `/health` endpoint
- **Platform**: Configured for Railway/Heroku deployment

## Current Configuration

### Database
- **Provider**: Neon PostgreSQL
- **Connection**: Configured via DATABASE_URL environment variable
- **Host**: ep-silent-glitter-a54ivu6n.us-east-2.aws.neon.tech
- **Database**: neondb
- **SSL Mode**: Required

### Application Entry Points
- **Production**: `app:app` (via Gunicorn in Procfile)
- **Development**: `main.py` (for local testing)

### Web Server
- **Server**: Gunicorn 21.2.0
- **Workers**: 2 gevent workers with 2 threads each
- **Timeout**: 120 seconds
- **Port**: Dynamic ($PORT environment variable)

## Deployment Platforms

### Railway (Recommended)
Your application is already configured for Railway with `railway.json`:

1. **Connect to Railway**
   - Go to https://railway.app
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

2. **Environment Variables** (Already in Replit Secrets)
   - SESSION_SECRET
   - DATABASE_URL
   - SENDGRID_API_KEY
   - SENDGRID_FROM_EMAIL
   - STRIPE_PUBLISHABLE_KEY_TEST
   - STRIPE_SECRET_KEY_TEST
   - STRIPE_WEBHOOK_SECRET
   - POSTHOG_API_KEY
   - CRISP_WEBSITE_ID
   - CRISP_MARKETPLACE_KEY
   - GEMINI_API_KEY

3. **Deploy**
   - Railway will automatically detect your configuration
   - It will use the `railway.json` configuration
   - Your app will be live in minutes!

### Heroku
If deploying to Heroku:

1. **Create Heroku App**
   ```bash
   heroku create your-app-name
   ```

2. **Set Environment Variables**
   ```bash
   heroku config:set SESSION_SECRET="your-secret"
   heroku config:set DATABASE_URL="your-database-url"
   # ... set all other variables from .env
   ```

3. **Deploy**
   ```bash
   git push heroku main
   ```

### Replit (Current Environment)
Your app is already running on Replit! To make it production-ready:

1. **Use the Deploy button** in Replit
2. **Set Secrets** (Already done - visible in your .env)
3. **Configure custom domain** if needed

## Health Check
Your application includes a comprehensive health check endpoint:
- **URL**: `/health`
- **Checks**: Database connection, Gemini service, environment variables
- **Use**: For monitoring and load balancer health checks

## Important Notes

### Security
✅ All sensitive credentials are in environment variables (not hardcoded)
✅ SESSION_SECRET is set for Flask sessions
✅ Database connection uses SSL
✅ CSRF protection should be enabled for forms

### Database
✅ Neon PostgreSQL is configured and ready
✅ Connection pooling via psycopg2
✅ All required tables will be created on startup
✅ Migration system in place

### API Keys
Your application uses:
- **Gemini API**: For AI/LLM features
- **SendGrid**: For email notifications
- **Stripe**: For payment processing (test mode)
- **PostHog**: For analytics
- **Crisp**: For customer support chat

## Verification Checklist

Before going live, verify:

- [ ] All environment variables are set in production
- [ ] Database connection is working (check /health)
- [ ] SSL certificates are properly configured
- [ ] Email sending works (test SendGrid)
- [ ] Stripe webhooks are configured
- [ ] Analytics are tracking correctly
- [ ] Health check endpoint returns 200 OK

## Application Structure

```
/tmp/cc-agent/59044310/project/
├── app.py                 # Flask application setup
├── main.py               # Development entry point
├── routes.py             # All route handlers
├── database.py           # Database management
├── models.py             # Data models
├── auth.py               # Authentication logic
├── gemini_service.py     # AI/LLM service
├── email_service.py      # Email functionality
├── stripe_service.py     # Payment processing
├── analytics_service.py  # Analytics tracking
├── Procfile              # Production server config
├── railway.json          # Railway deployment config
├── requirements.txt      # Python dependencies
└── templates/            # HTML templates
```

## Quick Deploy to Railway

1. Push your code to GitHub
2. Go to https://railway.app/new
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will auto-detect Python and deploy!
6. Add environment variables in Railway dashboard
7. Your app will be live at: https://your-app.railway.app

## Support
- Health check: https://your-domain.com/health
- Database: Neon PostgreSQL (automatically managed)
- Logs: Check Railway/Heroku dashboard for real-time logs

## Next Steps
1. **Deploy to Railway** - Easiest option, already configured
2. **Add custom domain** - Configure in Railway settings
3. **Enable HTTPS** - Automatic with Railway
4. **Set up monitoring** - Use PostHog (already integrated)
5. **Configure Stripe webhooks** - Point to your production URL

Your application is production-ready! 🚀

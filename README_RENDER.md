# Quick Render Deployment

## 🚀 One-Click Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## Quick Start

1. **Push code to GitHub**
2. **Click "Deploy to Render" button above**
3. **Configure environment variables**
4. **Done!**

## Manual Setup

See `RENDER_DEPLOYMENT.md` for complete instructions.

## Environment Variables Needed

- `DATABASE_URL` - Auto-provided by Render PostgreSQL
- `SECRET_KEY` - Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `DEBUG=False`
- `ENVIRONMENT=production`
- `ALLOWED_ORIGINS` - Your frontend domains

## After Deployment

1. Run migrations: `alembic upgrade head` (via Render Shell)
2. Test: `curl https://your-app.onrender.com/health`
3. Update mobile app `BASE_URL` to your Render URL


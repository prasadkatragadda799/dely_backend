# Render.com Deployment Guide for Dely Backend

Complete step-by-step guide to deploy your FastAPI backend on Render.com.

## Prerequisites

- Render.com account (free tier available)
- GitHub/GitLab/Bitbucket account (for Git deployment)
- Your backend code pushed to a Git repository

---

## Step 1: Prepare Your Code

### 1.1 Push to Git Repository

If you haven't already, push your code to GitHub/GitLab:

```bash
git init
git add .
git commit -m "Render deployment ready"
git remote add origin https://github.com/yourusername/dely-backend.git
git push -u origin main
```

### 1.2 Verify Files Are Ready

Make sure these files exist in your repository:
- ✅ `render.yaml` - Render configuration
- ✅ `Procfile` - Process file for Render
- ✅ `runtime.txt` - Python version
- ✅ `requirements.txt` - Dependencies (includes gunicorn)
- ✅ `wsgi.py` - WSGI entry point
- ✅ `.env.production.example` - Environment variables template

---

## Step 2: Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up (free tier available)
3. Connect your GitHub/GitLab account

---

## Step 3: Create PostgreSQL Database

1. **In Render Dashboard:**
   - Click **"New +"** → **"PostgreSQL"**

2. **Configure Database:**
   - **Name:** `dely-db`
   - **Database:** `dely_db`
   - **User:** `dely_user`
   - **Region:** Choose closest to your users
   - **Plan:** Free (or paid if needed)
   - Click **"Create Database"**

3. **Note Database Credentials:**
   - After creation, Render will show:
     - **Internal Database URL** (for services in same region)
     - **External Database URL** (for external connections)
   - Copy the **Internal Database URL** - you'll need it

---

## Step 4: Deploy Web Service

### Option A: Using render.yaml (Recommended)

1. **In Render Dashboard:**
   - Click **"New +"** → **"Blueprint"**
   - Connect your Git repository
   - Render will detect `render.yaml`
   - Click **"Apply"**

2. **Render will automatically:**
   - Create the web service
   - Create the database
   - Link them together

### Option B: Manual Setup

1. **In Render Dashboard:**
   - Click **"New +"** → **"Web Service"**

2. **Connect Repository:**
   - Select your Git provider (GitHub/GitLab)
   - Choose your repository: `dely-backend`
   - Click **"Connect"**

3. **Configure Service:**
   - **Name:** `dely-api`
   - **Region:** Same as database (for best performance)
   - **Branch:** `main` (or your default branch)
   - **Root Directory:** Leave empty (or `./` if needed)
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 4 --worker-class uvicorn.workers.UvicornWorker`

4. **Click "Create Web Service"**

---

## Step 5: Configure Environment Variables

1. **In your Web Service dashboard:**
   - Go to **"Environment"** tab
   - Click **"Add Environment Variable"**

2. **Add these variables:**

```env
# App Settings
APP_NAME=Dely API
APP_VERSION=1.0.0
DEBUG=False
ENVIRONMENT=production

# Database - Use Render's Internal Database URL
# Format: postgresql://user:password@host:port/database
# Get this from your PostgreSQL service dashboard
DATABASE_URL=<Your Render PostgreSQL Internal URL>

# JWT - Generate a strong secret key
# Run locally: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=<Your generated secret key - minimum 32 characters>

# CORS - Your frontend/mobile app domains
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourdomain.com

# Payment Gateway (optional)
PAYMENT_GATEWAY=razorpay
RAZORPAY_KEY_ID=your-key-id
RAZORPAY_KEY_SECRET=your-key-secret

# File Upload
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=10485760
ALLOWED_EXTENSIONS=jpg,jpeg,png,pdf

# CDN (optional)
CDN_BASE_URL=https://cdn.yourdomain.com
```

3. **Important:** 
   - For `DATABASE_URL`, use the **Internal Database URL** from your PostgreSQL service
   - It looks like: `postgresql://dely_user:password@dpg-xxxxx-a/dely_db`

---

## Step 6: Link Database to Web Service

1. **In your Web Service dashboard:**
   - Go to **"Environment"** tab
   - Scroll to **"Linked Resources"**
   - Click **"Link Resource"**
   - Select your PostgreSQL database
   - Render will automatically add `DATABASE_URL` environment variable

---

## Step 7: Run Database Migrations

### Option 1: Via Render Shell

1. **In your Web Service dashboard:**
   - Go to **"Shell"** tab
   - Click **"Open Shell"**

2. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

### Option 2: Via Local Connection

1. **Get External Database URL** from PostgreSQL service
2. **Set locally:**
   ```bash
   export DATABASE_URL=<External Database URL>
   alembic upgrade head
   ```

---

## Step 8: Deploy

1. **Render will automatically deploy** when you:
   - Push to your Git repository
   - Or click **"Manual Deploy"** → **"Deploy latest commit"**

2. **Monitor deployment:**
   - Watch the **"Logs"** tab
   - Wait for "Your service is live" message

3. **Get your API URL:**
   - Render provides: `https://dely-api.onrender.com` (or your custom domain)
   - Your API base URL: `https://dely-api.onrender.com/api/v1`

---

## Step 9: Test Your Deployment

### Health Check
```bash
curl https://dely-api.onrender.com/health
```

### Test Registration
```bash
curl -X POST https://dely-api.onrender.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "phone": "1234567890",
    "business_name": "Test Business",
    "password": "test123456",
    "confirm_password": "test123456"
  }'
```

---

## Step 10: Custom Domain (Optional)

1. **In your Web Service dashboard:**
   - Go to **"Settings"** tab
   - Scroll to **"Custom Domains"**
   - Click **"Add Custom Domain"**
   - Enter your domain: `api.yourdomain.com`
   - Follow DNS configuration instructions

2. **Update CORS:**
   - Add your custom domain to `ALLOWED_ORIGINS` environment variable
   - Redeploy the service

---

## Configuration Files Explained

### `render.yaml`
- Defines your infrastructure as code
- Automatically creates web service and database
- Sets environment variables and health checks

### `Procfile`
- Tells Render how to start your application
- Uses Gunicorn with Uvicorn workers for FastAPI

### `runtime.txt`
- Specifies Python version
- Render will use this version

---

## Troubleshooting

### Issue: Build fails

**Solutions:**
- Check `requirements.txt` for all dependencies
- Verify Python version in `runtime.txt`
- Check build logs in Render dashboard

### Issue: Database connection error

**Solutions:**
- Use **Internal Database URL** (not external)
- Verify database is in same region as web service
- Check `DATABASE_URL` environment variable

### Issue: Application crashes on startup

**Solutions:**
- Check logs in Render dashboard
- Verify all environment variables are set
- Ensure `SECRET_KEY` is set
- Check if database migrations ran successfully

### Issue: Slow cold starts

**Solutions:**
- Render free tier spins down after inactivity
- First request may take 30-60 seconds
- Upgrade to paid plan for always-on service
- Or use a ping service to keep it awake

---

## Render Free Tier Limitations

- **Spins down after 15 minutes of inactivity**
- **Cold starts:** First request after spin-down takes 30-60 seconds
- **512 MB RAM**
- **0.1 CPU share**

**Solutions:**
- Use a service like [UptimeRobot](https://uptimerobot.com) to ping your API every 5 minutes
- Or upgrade to paid plan ($7/month) for always-on service

---

## Environment Variables Reference

| Variable | Required | Description |
|---------|----------|-------------|
| `DATABASE_URL` | ✅ Yes | PostgreSQL connection string from Render |
| `SECRET_KEY` | ✅ Yes | JWT secret key (32+ characters) |
| `DEBUG` | ✅ Yes | Set to `False` in production |
| `ENVIRONMENT` | ✅ Yes | Set to `production` |
| `ALLOWED_ORIGINS` | ✅ Yes | Comma-separated list of allowed domains |
| `SMTP_*` | ❌ No | Email configuration (optional) |
| `RAZORPAY_*` | ❌ No | Payment gateway (optional) |

---

## Post-Deployment Checklist

- [ ] Health check endpoint works: `/health`
- [ ] Database migrations completed successfully
- [ ] Registration endpoint tested
- [ ] Login endpoint tested
- [ ] CORS configured correctly
- [ ] Custom domain configured (if applicable)
- [ ] SSL certificate active (automatic on Render)
- [ ] Environment variables all set
- [ ] Logs checked for errors

---

## Quick Deploy Commands

```bash
# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Test locally with Render database
export DATABASE_URL=<External Database URL>
alembic upgrade head
python run.py

# Push to trigger deployment
git add .
git commit -m "Deploy to Render"
git push origin main
```

---

## Support Resources

- Render Docs: https://render.com/docs
- FastAPI Docs: https://fastapi.tiangolo.com
- Render Status: https://status.render.com

---

**Your API will be available at:**
- Default: `https://dely-api.onrender.com`
- Custom: `https://api.yourdomain.com` (if configured)

**API Base URL:** `https://dely-api.onrender.com/api/v1`

**Good luck with your deployment! 🚀**


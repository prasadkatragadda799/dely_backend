# Quick Render Setup (5 Minutes)

## Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Render ready"
git remote add origin https://github.com/yourusername/dely-backend.git
git push -u origin main
```

## Step 2: Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Authorize Render

## Step 3: Create PostgreSQL Database

1. Click **"New +"** → **"PostgreSQL"**
2. Name: `dely-db`
3. Plan: **Free**
4. Region: Choose closest
5. Click **"Create Database"**
6. **Copy the Internal Database URL**

## Step 4: Deploy Web Service

### Using render.yaml (Easiest)

1. Click **"New +"** → **"Blueprint"**
2. Connect your GitHub repo
3. Render detects `render.yaml`
4. Click **"Apply"**
5. Done! (Database auto-created)

### Manual Setup

1. Click **"New +"** → **"Web Service"**
2. Connect GitHub repo
3. Configure:
   - **Name:** `dely-api`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 4 --worker-class uvicorn.workers.UvicornWorker`
4. Click **"Create Web Service"**

## Step 5: Set Environment Variables

In your Web Service → **Environment** tab:

```env
DATABASE_URL=<Internal Database URL from PostgreSQL>
SECRET_KEY=<Generate: python -c "import secrets; print(secrets.token_urlsafe(32))">
DEBUG=False
ENVIRONMENT=production
ALLOWED_ORIGINS=https://yourdomain.com
```

## Step 6: Run Migrations

1. Web Service → **Shell** tab
2. Click **"Open Shell"**
3. Run: `alembic upgrade head`

## Step 7: Test

```bash
curl https://dely-api.onrender.com/health
```

## ✅ Done!

Your API is live at: `https://dely-api.onrender.com/api/v1`

---

**Full guide:** See `RENDER_DEPLOYMENT.md`


# Quick Render Deployment Guide

## 🚀 Fast Deployment (5 minutes)

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### Step 2: Deploy on Render

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +"** → **"Blueprint"** (or use individual services)

#### Option A: Using Blueprint (render.yaml) - RECOMMENDED
1. Click **"New +"** → **"Blueprint"**
2. Connect your GitHub repository
3. Render will automatically detect `render.yaml`
4. Review configuration and click **"Apply"**
5. Render will create both database and web service automatically

#### Option B: Manual Setup

**Create Database:**
1. Click **"New +"** → **"PostgreSQL"**
2. Name: `dely-db`
3. Click **"Create Database"**
4. Copy the **Internal Database URL**

**Create Web Service:**
1. Click **"New +"** → **"Web Service"**
2. Connect GitHub repository
3. Configure:
   - **Name**: `dely-api`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && alembic upgrade head`
   - **Start Command**: `gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 4 --worker-class uvicorn.workers.UvicornWorker`
4. Add Environment Variables:
   - `DATABASE_URL` = (Internal Database URL from step above)
   - `SECRET_KEY` = (Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
   - `DEBUG` = `False`
   - `ENVIRONMENT` = `production`
5. Click **"Create Web Service"**

### Step 3: Create Admin User

After deployment completes:

1. Go to your Web Service → **"Shell"** tab
2. Run:
```bash
python create_admin.py
```
3. Enter admin credentials when prompted

### Step 4: Test Your API

Your API will be available at:
- **Base URL**: `https://your-service-name.onrender.com`
- **Health Check**: `https://your-service-name.onrender.com/health`
- **API Docs**: `https://your-service-name.onrender.com/docs` (disabled in production)

### Step 5: Test Admin Login

```bash
curl -X POST https://your-service-name.onrender.com/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@dely.com", "password": "your-password"}'
```

## ✅ Checklist

- [ ] Code pushed to GitHub
- [ ] Database created on Render
- [ ] Web service created on Render
- [ ] Environment variables set
- [ ] Migrations ran successfully
- [ ] Admin user created
- [ ] Health check passes
- [ ] Admin login works

## 🔧 Important Notes

1. **Free Tier**: Services spin down after 15 min inactivity (first request takes ~30s)
2. **Database URL**: Use Internal URL (faster, free) not External URL
3. **SECRET_KEY**: Must be set in environment variables (never commit to git)
4. **File Uploads**: Use cloud storage (S3/Cloudinary) - Render filesystem is ephemeral
5. **CORS**: Update `ALLOWED_ORIGINS` with your frontend domain

## 🐛 Troubleshooting

**Service won't start:**
- Check logs in Render dashboard
- Verify `DATABASE_URL` is correct
- Ensure `SECRET_KEY` is set

**Database errors:**
- Verify migrations ran: Check build logs
- Run manually: `alembic upgrade head` in Shell

**502 Bad Gateway:**
- Service might be spinning up (wait 30 seconds)
- Check service logs for errors

## 📚 Full Documentation

See `RENDER_DEPLOYMENT_STEPS.md` for detailed instructions.


# Quick Deployment Summary

## 🚀 Fast Deployment Steps

### 1. Generate Secret Key
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Upload Files to Hostinger
- Upload entire project to `/home/username/dely-backend`
- Exclude: `venv/`, `.env`, `*.db`, `__pycache__/`

### 3. Create MySQL Database
- Hostinger Control Panel → Databases → MySQL
- Create database and user
- Note credentials

### 4. SSH into Hostinger
```bash
ssh username@yourdomain.com
cd ~/dely-backend
```

### 5. Set Up Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6. Create .env File
```bash
nano .env
# Copy from .env.production.example and update:
# - DATABASE_URL (MySQL credentials)
# - SECRET_KEY (from step 1)
# - ALLOWED_ORIGINS (your domains)
```

### 7. Run Migrations
```bash
alembic upgrade head
```

### 8. Configure Python App in Hostinger
- Control Panel → Python App
- Startup File: `wsgi.py`
- Working Directory: `/home/username/dely-backend`
- Virtual Environment: `/home/username/dely-backend/venv`

### 9. Test
```bash
curl https://api.yourdomain.com/health
```

## 📋 Full Guide
See `HOSTINGER_DEPLOYMENT.md` for detailed instructions.

## ✅ Checklist
See `DEPLOYMENT_CHECKLIST.md` before deploying.


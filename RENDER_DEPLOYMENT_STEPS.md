# Render Deployment Steps

## Prerequisites
1. GitHub account with your code pushed to a repository
2. Render account (sign up at https://render.com)

## Step 1: Create PostgreSQL Database on Render

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name**: `dely-db` (or your preferred name)
   - **Database**: `dely_db`
   - **User**: `dely_user` (auto-generated)
   - **Region**: Choose closest to your users
   - **PostgreSQL Version**: 15 (or latest)
   - **Plan**: Free tier (or paid for production)
4. Click **"Create Database"**
5. **IMPORTANT**: Copy the **Internal Database URL** (you'll need this)

## Step 2: Create Web Service on Render

1. In Render dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure the service:
   - **Name**: `dely-backend` (or your preferred name)
   - **Environment**: `Python 3`
   - **Region**: Same as database
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty (or `backend` if your code is in a subdirectory)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
   - **Plan**: Free tier (or paid for production)

## Step 3: Configure Environment Variables

In your Web Service settings, go to **"Environment"** and add:

### Required Variables:
```
DATABASE_URL=<your-postgresql-internal-url-from-step-1>
SECRET_KEY=<generate-a-random-secret-key>
DEBUG=False
ENVIRONMENT=production
```

### Optional Variables (configure as needed):
```
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@dely.com
RAZORPAY_KEY_ID=your-razorpay-key
RAZORPAY_KEY_SECRET=your-razorpay-secret
```

### Generate SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Run migrations (if configured)
   - Start your service

## Step 5: Run Database Migrations

After deployment, you need to run migrations:

### Option A: Using Render Shell
1. Go to your Web Service
2. Click **"Shell"** tab
3. Run:
```bash
alembic upgrade head
```

### Option B: Using SSH (if enabled)
```bash
ssh <your-service>@ssh.render.com
cd /opt/render/project/src
alembic upgrade head
```

### Option C: Add to Build Command
Add to your build command:
```bash
pip install -r requirements.txt && alembic upgrade head
```

## Step 6: Create Admin User

After migrations, create your first admin:

### Using Render Shell:
```bash
python create_admin.py
```

Or manually via Python:
```python
from app.database import SessionLocal
from app.models.admin import Admin, AdminRole
from app.utils.security import get_password_hash
from uuid import uuid4

db = SessionLocal()
admin = Admin(
    id=uuid4(),
    email="admin@dely.com",
    password_hash=get_password_hash("your-secure-password"),
    name="Admin User",
    role=AdminRole.SUPER_ADMIN,
    is_active=True
)
db.add(admin)
db.commit()
```

## Step 7: Verify Deployment

1. Check your service URL: `https://your-service-name.onrender.com`
2. Health check: `https://your-service-name.onrender.com/health`
3. API docs: `https://your-service-name.onrender.com/docs` (if DEBUG=True)
4. Test admin login: `POST /admin/auth/login`

## Important Notes

### Free Tier Limitations:
- Services spin down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds
- Upgrade to paid plan for always-on service

### Database Connection:
- Use **Internal Database URL** for `DATABASE_URL` (faster, free)
- External URL works but is slower and may have rate limits

### File Uploads:
- Render's filesystem is ephemeral (files deleted on restart)
- Use cloud storage (S3, Cloudinary) for production
- Update `app/api/v1/admin_upload.py` to use cloud storage

### Logs:
- View logs in Render dashboard
- Check "Logs" tab in your service
- Errors are automatically logged

## Troubleshooting

### Service won't start:
- Check logs in Render dashboard
- Verify `DATABASE_URL` is correct
- Ensure all dependencies are in `requirements.txt`

### Database connection errors:
- Verify `DATABASE_URL` uses internal URL
- Check database is running
- Ensure migrations ran successfully

### 502 Bad Gateway:
- Service might be spinning up (wait 30 seconds)
- Check logs for errors
- Verify `gunicorn` command is correct

### Migrations not running:
- Run manually via Shell
- Or add to build command
- Check `alembic.ini` configuration

## Next Steps

1. Set up custom domain (optional)
2. Configure SSL (automatic on Render)
3. Set up monitoring/alerts
4. Configure backups for database
5. Set up CI/CD for auto-deployment

## Support

- Render Docs: https://render.com/docs
- Render Community: https://community.render.com


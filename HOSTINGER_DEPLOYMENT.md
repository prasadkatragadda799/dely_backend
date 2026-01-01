# Hostinger Deployment Guide for Dely Backend

Complete step-by-step guide to deploy your FastAPI backend on Hostinger.

## Prerequisites

- Hostinger hosting account with Python support
- Domain name (optional, can use subdomain)
- MySQL database access from Hostinger control panel
- FTP/SFTP access or Git repository access

---

## Step 1: Prepare Your Project

### 1.1 Generate Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Save this key - you'll need it for the `.env` file.

### 1.2 Update Requirements

Make sure `requirements.txt` includes MySQL support (already done).

### 1.3 Test Locally

```bash
# Test with MySQL connection string
python -c "from app.main import app; print('App loads successfully')"
```

---

## Step 2: Upload Files to Hostinger

### Option A: Using FTP/SFTP

1. **Connect to Hostinger via FTP/SFTP**
   - Use FileZilla or similar FTP client
   - Host: `ftp.yourdomain.com` or IP from Hostinger
   - Username/Password: From Hostinger control panel

2. **Upload Project Files**
   - Upload entire `backend` folder to: `/home/username/dely-backend`
   - **DO NOT upload:**
     - `dely.db` (SQLite file)
     - `__pycache__/` folders
     - `.env` file (create on server)
     - `logs/` folder (will be created automatically)
     - `venv/` folder (create on server)

### Option B: Using Git (Recommended)

1. **Push to Git Repository**
   ```bash
   git init
   git add .
   git commit -m "Production ready"
   git remote add origin your-git-repo-url
   git push -u origin main
   ```

2. **Clone on Hostinger**
   - SSH into Hostinger
   - Navigate to your domain directory
   - Clone repository:
     ```bash
     git clone your-git-repo-url dely-backend
     cd dely-backend
     ```

---

## Step 3: Create MySQL Database

1. **Login to Hostinger Control Panel**
   - Go to **Databases** → **MySQL Databases**

2. **Create Database**
   - Database Name: `dely_db` (or your choice)
   - Click **Create**

3. **Create Database User**
   - Username: `dely_user` (or your choice)
   - Password: Generate strong password
   - Click **Create User**

4. **Grant Privileges**
   - Select user and database
   - Click **Add User to Database**
   - Grant **ALL PRIVILEGES**
   - Click **Make Changes**

5. **Note Database Details**
   - Database Name: `username_dely_db`
   - Username: `username_dely_user`
   - Host: Usually `localhost`
   - Port: `3306`

---

## Step 4: Set Up Python Environment

### 4.1 SSH into Hostinger

```bash
ssh username@yourdomain.com
# Or use Hostinger's SSH access from control panel
```

### 4.2 Navigate to Project Directory

```bash
cd ~/dely-backend
# Or wherever you uploaded the files
```

### 4.3 Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4.4 Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note:** If you get errors, you might need to install system packages:
```bash
# On some Hostinger servers
sudo apt-get update
sudo apt-get install python3-dev default-libmysqlclient-dev build-essential
```

---

## Step 5: Configure Environment Variables

### 5.1 Create .env File

```bash
cd ~/dely-backend
nano .env
```

### 5.2 Add Production Configuration

Copy from `.env.production.example` and update:

```env
# App Settings
APP_NAME=Dely API
APP_VERSION=1.0.0
DEBUG=False
ENVIRONMENT=production

# Database - Use your MySQL credentials from Step 3
DATABASE_URL=mysql+pymysql://username_dely_user:your_password@localhost:3306/username_dely_db

# JWT - Use the secret key from Step 1.1
SECRET_KEY=your-generated-secret-key-here

# CORS - Your actual domains
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Email (if needed)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourdomain.com

# Payment Gateway (if using)
PAYMENT_GATEWAY=razorpay
RAZORPAY_KEY_ID=your-key-id
RAZORPAY_KEY_SECRET=your-key-secret
```

### 5.3 Secure .env File

```bash
chmod 600 .env
```

---

## Step 6: Run Database Migrations

```bash
# Activate virtual environment
source venv/bin/activate

# Run migrations
alembic upgrade head
```

If you get errors, check:
- Database credentials in `.env`
- MySQL service is running
- User has proper permissions

---

## Step 7: Configure Hostinger Python App

### 7.1 Access Python App Settings

1. Login to Hostinger Control Panel
2. Go to **Advanced** → **Python App** (or **Websites** → **Python App**)

### 7.2 Create/Configure Python App

1. **App Name:** `dely-api`
2. **Python Version:** Select Python 3.9 or higher
3. **App Directory:** `/home/username/dely-backend`
4. **App URL:** `https://api.yourdomain.com` (or your subdomain)
5. **Startup File:** `wsgi.py`
6. **Working Directory:** `/home/username/dely-backend`
7. **Virtual Environment:** `/home/username/dely-backend/venv`

### 7.3 Save Configuration

Click **Save** or **Create App**

---

## Step 8: Create Required Directories

```bash
cd ~/dely-backend
mkdir -p uploads logs
chmod 755 uploads logs
```

---

## Step 9: Test the Deployment

### 9.1 Check App Status

In Hostinger control panel, check if Python app is running.

### 9.2 Test API Endpoints

```bash
# Health check
curl https://api.yourdomain.com/health

# Or visit in browser
https://api.yourdomain.com/health
```

### 9.3 Test Registration

```bash
curl -X POST https://api.yourdomain.com/api/v1/auth/register \
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

## Step 10: SSL/HTTPS Configuration

1. **Enable SSL in Hostinger**
   - Go to **SSL** in control panel
   - Enable **Free SSL** (Let's Encrypt)
   - Wait for activation (usually 5-10 minutes)

2. **Force HTTPS** (Optional)
   - Add redirect in `.htaccess` if needed
   - Or configure in Hostinger settings

---

## Step 11: Domain Configuration

### 11.1 Subdomain Setup (Recommended)

1. **Create Subdomain**
   - Go to **Domains** → **Subdomains**
   - Create: `api.yourdomain.com`
   - Point to your Python app directory

2. **Update DNS** (if needed)
   - Add A record: `api` → Your server IP
   - Or use Hostinger's automatic DNS

### 11.2 Update CORS Settings

Update `.env` with your actual domain:
```env
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

Restart the app in Hostinger control panel.

---

## Step 12: Monitoring and Logs

### 12.1 Check Logs

```bash
# Application logs
tail -f ~/dely-backend/logs/app.log

# Error logs
tail -f ~/dely-backend/logs/error.log

# Hostinger Python app logs
# Check in Hostinger control panel → Python App → Logs
```

### 12.2 Monitor Performance

- Check Hostinger control panel for resource usage
- Monitor database connections
- Watch for errors in logs

---

## Troubleshooting

### Issue: App won't start

**Solutions:**
- Check Python version (must be 3.9+)
- Verify `wsgi.py` exists and is correct
- Check virtual environment path
- Review Hostinger Python app logs

### Issue: Database connection error

**Solutions:**
- Verify MySQL credentials in `.env`
- Check database user permissions
- Ensure MySQL service is running
- Test connection: `mysql -u username -p database_name`

### Issue: Module not found

**Solutions:**
- Ensure virtual environment is activated
- Reinstall requirements: `pip install -r requirements.txt`
- Check Python path in Hostinger settings

### Issue: 500 Internal Server Error

**Solutions:**
- Check error logs: `logs/error.log`
- Enable DEBUG temporarily to see details
- Verify all environment variables are set
- Check file permissions

### Issue: CORS errors

**Solutions:**
- Update `ALLOWED_ORIGINS` in `.env`
- Restart Python app
- Check if domain matches exactly (including https://)

---

## Security Checklist

- [ ] Strong `SECRET_KEY` set (32+ characters)
- [ ] `DEBUG=False` in production
- [ ] `.env` file has correct permissions (600)
- [ ] Database credentials are secure
- [ ] CORS origins are restricted to your domains
- [ ] SSL/HTTPS enabled
- [ ] API docs disabled in production (`docs_url=None`)
- [ ] File upload directory has proper permissions
- [ ] Logs directory is not publicly accessible

---

## Post-Deployment

### 1. Disable API Documentation (Optional)

Already configured - docs are disabled when `DEBUG=False`.

### 2. Set Up Backups

- Database backups via Hostinger control panel
- Code backups via Git
- Regular `.env` backups (store securely)

### 3. Performance Optimization

- Enable caching (if using Redis)
- Optimize database queries
- Use CDN for static files
- Monitor and optimize slow queries

### 4. Update Mobile App

Update your mobile app's `BASE_URL` to:
```
https://api.yourdomain.com/api/v1
```

---

## Quick Reference

### Important Paths
- Project: `/home/username/dely-backend`
- Virtual Env: `/home/username/dely-backend/venv`
- Logs: `/home/username/dely-backend/logs`
- Uploads: `/home/username/dely-backend/uploads`

### Useful Commands

```bash
# Activate virtual environment
source ~/dely-backend/venv/bin/activate

# Run migrations
cd ~/dely-backend && alembic upgrade head

# Check app status
# (In Hostinger control panel)

# View logs
tail -f ~/dely-backend/logs/app.log
```

### Restart App

In Hostinger control panel:
1. Go to **Python App**
2. Click **Restart** or **Reload**

---

## Support

- Hostinger Support: https://www.hostinger.com/contact
- FastAPI Docs: https://fastapi.tiangolo.com
- Project README: See `README.md`

---

**Your API will be available at:**
- Production: `https://api.yourdomain.com`
- Health Check: `https://api.yourdomain.com/health`
- API Base: `https://api.yourdomain.com/api/v1`

**Good luck with your deployment! 🚀**


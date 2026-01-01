# Hostinger SSH Deployment Guide

Since Hostinger doesn't have a direct "Python App" option, we'll deploy via SSH.

## Prerequisites

1. **Enable SSH Access**
   - Go to: **Advanced** → **SSH Access**
   - Enable SSH if not already enabled
   - Note your SSH credentials (username, host, port)

2. **Database Already Created** ✅
   - Database: `u301511266_dely_db`
   - User: `u301511266_prasadkatra_gad`
   - You'll need the password for this user

## Step 1: Upload Files via FTP/File Manager

1. **Using File Manager:**
   - Go to **Files** in left sidebar
   - Navigate to your website root (usually `public_html` or `delycart.gdnidhi.com`)
   - Create folder: `dely-backend`
   - Upload all your backend files

2. **Or use FTP:**
   - Use FileZilla with Hostinger FTP credentials
   - Upload to: `/home/u301511266/delycart.gdnidhi.com/dely-backend`

## Step 2: SSH into Hostinger

```bash
ssh u301511266@delycart.gdnidhi.com
# Or use the host provided by Hostinger
```

## Step 3: Navigate and Set Up

```bash
# Navigate to your project
cd ~/delycart.gdnidhi.com/dely-backend
# OR if files are in public_html:
cd ~/public_html/dely-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 4: Create .env File

```bash
nano .env
```

Add this content (update with your actual values):

```env
# App Settings
APP_NAME=Dely API
APP_VERSION=1.0.0
DEBUG=False
ENVIRONMENT=production

# Database - Use your existing database
DATABASE_URL=mysql+pymysql://u301511266_prasadkatra_gad:YOUR_DB_PASSWORD@localhost:3306/u301511266_dely_db

# JWT - Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=YOUR_GENERATED_SECRET_KEY_HERE

# CORS
ALLOWED_ORIGINS=https://delycart.gdnidhi.com

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=noreply@delycart.gdnidhi.com
```

Save: `Ctrl+X`, then `Y`, then `Enter`

## Step 5: Run Migrations

```bash
source venv/bin/activate
alembic upgrade head
```

## Step 6: Test the Server

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If it works, press `Ctrl+C` to stop.

## Step 7: Run as Background Service

### Option A: Using screen (Recommended)

```bash
# Install screen if not available
# Create a screen session
screen -S dely-api

# Inside screen, start server
cd ~/delycart.gdnidhi.com/dely-backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Detach: Press Ctrl+A, then D
# Reattach: screen -r dely-api
```

### Option B: Using nohup

```bash
cd ~/delycart.gdnidhi.com/dely-backend
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

### Option C: Create systemd service (if you have root access)

Create `/etc/systemd/system/dely-api.service`:

```ini
[Unit]
Description=Dely API FastAPI Application
After=network.target

[Service]
User=u301511266
WorkingDirectory=/home/u301511266/delycart.gdnidhi.com/dely-backend
Environment="PATH=/home/u301511266/delycart.gdnidhi.com/dely-backend/venv/bin"
ExecStart=/home/u301511266/delycart.gdnidhi.com/dely-backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable dely-api
sudo systemctl start dely-api
sudo systemctl status dely-api
```

## Step 8: Configure Domain/Subdomain

1. **In Hostinger Panel:**
   - Go to **Domains** → **DNS Zone Editor**
   - Add A record: `api` → Your server IP
   - Or use subdomain: `api.delycart.gdnidhi.com`

2. **Or use existing domain:**
   - Access via: `https://delycart.gdnidhi.com:8000` (if port is open)
   - Or configure reverse proxy (if available)

## Step 9: Test Your API

```bash
# Health check
curl https://delycart.gdnidhi.com/health
# Or
curl http://delycart.gdnidhi.com:8000/health
```

## Troubleshooting

### Can't find SSH Access
- Check **Advanced** section in left sidebar
- Contact Hostinger support to enable SSH
- Or use FTP + Cron Jobs method (see below)

### Port 8000 not accessible
- Check Hostinger firewall settings
- Use port 80 or 443 if available
- Or configure reverse proxy

### Server stops when SSH disconnects
- Use `screen` or `tmux` to keep it running
- Or use `nohup` command
- Or set up as systemd service

## Alternative: Using Cron Job (If no SSH)

1. Go to **Advanced** → **Cron Jobs**
2. Create cron job that runs a script to start server
3. This is less ideal but works if SSH unavailable

---

**Your API should now be running!** 🚀


# EC2 Deployment Guide (Ubuntu + systemd + Nginx)

This guide deploys the backend directly on an EC2 Ubuntu instance.

## 1) Prepare EC2

- Launch Ubuntu EC2 (22.04 or newer)
- Open Security Group ports:
  - `22` (SSH)
  - `80` (HTTP)
  - `443` (HTTPS)

## 2) Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx
```

## 3) Copy project and install dependencies

```bash
sudo mkdir -p /var/www/dely_backend
sudo chown -R $USER:$USER /var/www/dely_backend

# copy your project files into /var/www/dely_backend
cd /var/www/dely_backend

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
chmod +x start.sh
```

## 4) Configure environment

```bash
cp .env.ec2.example .env
nano .env
```

Required values:
- `ENVIRONMENT=production`
- `DEBUG=false`
- `SECRET_KEY` (strong random value)
- `DATABASE_URL`
- `ALLOWED_ORIGINS`

## 5) Run migrations once manually

```bash
source venv/bin/activate
alembic upgrade head
```

## 6) Configure systemd service

```bash
sudo cp deploy/ec2/dely-backend.service /etc/systemd/system/dely-backend.service
sudo sed -i "s|User=ubuntu|User=$USER|g" /etc/systemd/system/dely-backend.service

sudo systemctl daemon-reload
sudo systemctl enable dely-backend
sudo systemctl start dely-backend
sudo systemctl status dely-backend
```

Logs:

```bash
journalctl -u dely-backend -f
```

## 7) Configure Nginx reverse proxy

```bash
sudo cp deploy/ec2/nginx-dely-backend.conf /etc/nginx/sites-available/dely-backend
# edit server_name to your domain
sudo nano /etc/nginx/sites-available/dely-backend

sudo ln -s /etc/nginx/sites-available/dely-backend /etc/nginx/sites-enabled/dely-backend
sudo nginx -t
sudo systemctl reload nginx
```

## 8) Enable HTTPS (Let's Encrypt)

```bash
sudo certbot --nginx -d api.yourdomain.com
```

## 9) Verify

```bash
curl http://127.0.0.1:8000/health
curl https://api.yourdomain.com/health
```

## Optional tuning

- Adjust `WEB_CONCURRENCY` in `.env` based on EC2 size
- Set `RUN_MIGRATIONS=false` if you want migrations only in CI/CD

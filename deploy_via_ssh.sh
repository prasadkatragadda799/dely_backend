#!/bin/bash
# Deployment script for Hostinger via SSH

echo "=== Dely Backend Deployment Script ==="

# Navigate to project directory
cd ~/delycart.gdnidhi.com/dely-backend || cd ~/public_html/dely-backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create required directories
mkdir -p uploads logs
chmod 755 uploads logs

# Run migrations
echo "Running database migrations..."
alembic upgrade head

echo "=== Deployment Complete ==="
echo "Next steps:"
echo "1. Create .env file with your database credentials"
echo "2. Start the server with: source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"


#!/bin/bash
# Script to find the backend directory

echo "=== Finding Backend Directory ==="

# Try common paths
echo "Checking common paths..."

# Path 1: public_html
if [ -d ~/public_html/dely_backend/backend ]; then
    echo "✓ Found at: ~/public_html/dely_backend/backend"
    cd ~/public_html/dely_backend/backend
    pwd
    ls -la
    exit 0
fi

# Path 2: domains structure
if [ -d ~/domains/delycart.gdnidhi.com/public_html/dely_backend/backend ]; then
    echo "✓ Found at: ~/domains/delycart.gdnidhi.com/public_html/dely_backend/backend"
    cd ~/domains/delycart.gdnidhi.com/public_html/dely_backend/backend
    pwd
    ls -la
    exit 0
fi

# Path 3: Just public_html/backend
if [ -d ~/public_html/backend ]; then
    echo "✓ Found at: ~/public_html/backend"
    cd ~/public_html/backend
    pwd
    ls -la
    exit 0
fi

# Search for it
echo "Searching for backend directory..."
find ~ -type d -name "backend" -path "*/dely_backend/*" 2>/dev/null | head -5

echo ""
echo "Current directory:"
pwd
echo ""
echo "Contents of ~:"
ls -la ~ | head -20


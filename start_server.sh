#!/bin/bash
# Start FastAPI server script

cd ~/delycart.gdnidhi.com/dely-backend || cd ~/public_html/dely-backend
source venv/bin/activate

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000


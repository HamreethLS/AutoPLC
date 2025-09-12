#!/bin/bash
# AutoPLC Enhanced Startup Script

echo "🚀 Starting AutoPLC Enhanced v2.0..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Initialize knowledge base
echo "Initializing knowledge base..."
python backend/ingest.py

# Check environment configuration
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Please copy .env.example to .env and configure your API keys."
    echo "Example: cp .env.example .env"
    exit 1
fi

# Start the application
echo "✅ Starting AutoPLC Enhanced server..."
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend

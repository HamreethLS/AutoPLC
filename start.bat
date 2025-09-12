@echo off
echo 🚀 Starting AutoPLC Enhanced v2.0...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/update dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Install Playwright browsers
playwright install chromium

REM Initialize knowledge base
echo Initializing knowledge base...
python backend\ingest.py

REM Check environment configuration
if not exist ".env" (
    echo ⚠️  No .env file found. Please copy .env.example to .env and configure your API keys.
    echo Example: copy .env.example .env
    pause
    exit /b 1
)

REM Start the application
echo ✅ Starting AutoPLC Enhanced server...
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend
pause

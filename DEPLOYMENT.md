# AutoPLC Deployment Guide

## 🚀 Complete Setup Instructions

### Step 1: Get NVIDIA NIM API Keys

1. Go to [NVIDIA Build](https://build.nvidia.com/)
2. Create a free account or log in
3. Select any model (e.g., Llama 3.1-70B Instruct)
4. Click **"Get API Key"** → **"Generate Key"**  
5. Copy the key (starts with `nvapi-`)
6. **Optional**: Create a second API key for redundancy

### Step 2: Clone and Setup Project

```bash
# Clone repository
git clone https://github.com/your-username/autoplc
cd autoplc

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup Playwright (for web scraping)
playwright install chromium
```

### Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your API keys
# Required:
NVIDIA_API_KEY_1=nvapi-your-actual-key-here
NVIDIA_API_KEY_2=nvapi-your-second-key-here

# Optional (for web search):
TAVILY_API_KEY=tvly-your-tavily-key-here

# Optional (for simulation):
OPENPLC_URL=http://localhost:8080
MATIEC_PATH=C:\path\to\your\matiec\installation
```

### Step 4: Initialize Knowledge Base

```bash
# First-time setup (creates vector database)
python backend/ingest.py

# You should see:
# --- Starting Knowledge Base Ingestion Process ---
# --- Ingestion Process Complete ---
```

### Step 5: Start the Application

```bash
# Start the enhanced backend server
python backend/app.py

# You should see:
# 🚀 Starting Enhanced AutoPLC Backend Server...
# 📡 NIM Client initialized with model routing
# 🔧 Simulator agent ready for OpenPLC/ScadaBR integration
# 💾 Knowledge base initialized
# 🌐 Server will be available at http://localhost:5001
```

### Step 6: Access the Application

1. Open your browser and go to: **http://localhost:5001**
2. You'll see the modern AutoPLC UI
3. Try an example prompt like: *"Control a conveyor belt system with start/stop buttons"*
4. Watch the agents collaborate in real-time!

---

## 🔧 Advanced Configuration

### Model Assignment Customization

Add to your `.env` file to override default models:

```bash
# Advanced model configuration
NIM_MODEL_PLANNER=meta/llama-3.1-70b-instruct
NIM_MODEL_CODER=meta/llama-3.1-70b-instruct  
NIM_MODEL_VALIDATOR=mistralai/mistral-7b-instruct-v0.3
NIM_MODEL_KNOWLEDGE=microsoft/phi-4-mini-instruct
NIM_MODEL_RETRIEVER=mistralai/mistral-7b-instruct-v0.3
```

### OpenPLC Simulation Setup (Optional)

1. Download [OpenPLC Runtime](https://openplcproject.com/)
2. Install and start on port 8080
3. Update `.env` with correct URL
4. Test simulation features in AutoPLC

### Production Deployment

```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 backend.app:app

# Or with Waitress (Windows-friendly)
pip install waitress
waitress-serve --host=0.0.0.0 --port=5001 backend.app:app
```

---

## 🐛 Troubleshooting

### Common Issues

**1. "NVIDIA_API_KEY_1 not found"**
- Make sure your `.env` file exists in the project root
- Check that your API key starts with `nvapi-`
- Verify the environment file is properly loaded

**2. "Knowledge base is empty"**
- Run `python backend/ingest.py` to initialize the knowledge base
- Check that ChromaDB can create files in the project directory

**3. "Module not found" errors**
- Make sure your virtual environment is activated
- Run `pip install -r requirements.txt` again
- Check Python version is 3.8 or higher

**4. Compilation errors with generated code**
- Verify MATIEC path in `.env` is correct
- Check that the MATIEC compiler is installed and accessible
- Try running `iec2c --help` from the MATIEC directory

**5. Slow response times**
- This is normal for first requests (model loading)
- Subsequent requests should be much faster
- Consider upgrading to paid NVIDIA NIM plan for better performance

### API Rate Limits

NVIDIA NIM free tier includes:
- 1,000 credits for new users
- Rate limiting may apply for high usage
- Consider getting additional API keys if needed

### Development Mode

For development with auto-reload:

```bash
# Set Flask environment
export FLASK_ENV=development
export FLASK_DEBUG=True

# Run with auto-reload
python backend/app.py
```

---

## 📊 Testing the System

### 1. Basic Functionality Test

Try this simple prompt:
```
Generate a basic start/stop motor control system
```

Expected: Agent conversation → Generated ST code → Successful compilation

### 2. Complex System Test

Try this advanced prompt:
```  
Create a batch mixing system with ingredient selection, timing sequences, and safety interlocks
```

Expected: Multiple agent interactions → Complex ST code → Detailed plan → Working simulation
### 3. Error Recovery Test

Deliberately break something to test error handling:
- Try with invalid API key
- Test with network disconnection
- Verify graceful error messages

---

## 🎪 Demo Preparation

### Pre-Demo Checklist

- [ ] API keys working and credited
- [ ] Knowledge base initialized
- [ ] Test a few example prompts  
- [ ] UI loads quickly at http://localhost:5001
- [ ] Agent conversation shows in real-time
- [ ] Code generation works end-to-end
- [ ] Optional: OpenPLC simulation ready

### Demo Script (5 minutes)

1. **Opening (30s)**: Show clean UI, explain multi-agent approach
2. **Live Generation (2m)**: Enter complex prompt, show agent collaboration
3. **Code Review (1m)**: Show generated ST code, highlight syntax validation
4. **Simulation (1m)**: Demonstrate OpenPLC integration (if available)
5. **Technical Highlights (30s)**: Model routing, production features

### Backup Plans

- Have screenshots/video ready if live demo fails
- Prepare multiple example prompts of varying complexity  
- Test everything on a different network/machine beforehand

---

## ✨ Success Indicators

You'll know everything is working correctly when:

1. ✅ Server starts with all green status messages
2. ✅ Modern UI loads at http://localhost:5001  
3. ✅ Agent conversation appears in real-time
4. ✅ Generated code compiles successfully
5. ✅ No error messages in console/logs

**Ready to generate some amazing PLC code! 🚀**
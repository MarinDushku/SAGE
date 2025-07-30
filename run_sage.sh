#!/bin/bash
# SAGE Startup Script
# Activates virtual environment and runs SAGE

echo "🚀 Starting SAGE with virtual environment..."
echo "   Activating virtual environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found! Please run:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
echo "   Checking dependencies..."
python -c "import pyttsx3" 2>/dev/null || {
    echo "⚠️  pyttsx3 not found, voice synthesis may not work"
}

python -c "import whisper" 2>/dev/null || {
    echo "⚠️  openai-whisper not found, advanced speech recognition unavailable"
}

echo "   Starting SAGE..."
python main.py

echo "✅ SAGE shutdown complete"
#!/bin/bash
# Quick start script for the Resource Matching API

echo "🚀 Starting AidConnect Resource Matching API..."
echo ""

# Check if we're in the right directory
if [ ! -f "flask_api.py" ]; then
    echo "❌ Error: flask_api.py not found!"
    echo "Please run this script from the mcp-hub directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found!"
    echo "Please install Python 3"
    exit 1
fi

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not found. Installing dependencies..."
    pip3 install flask flask-cors
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

echo "✅ Starting server on http://localhost:5002"
echo "📝 Press Ctrl+C to stop"
echo ""

python3 flask_api.py

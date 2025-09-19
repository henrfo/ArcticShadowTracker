#!/bin/bash
# Arctic Shadow Tracker - Live Dashboard Startup Script

echo "🌊 Arctic Shadow Tracker - Live Dashboard"
echo "========================================"
echo ""
echo "Starting live surveillance dashboard..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    echo "💡 Please install Python 3 and try again"
    exit 1
fi

# Check if config.yaml exists
if [ ! -f "config.yaml" ]; then
    echo "❌ config.yaml not found"
    echo "💡 Please ensure config.yaml is in the current directory"
    exit 1
fi

# Create arctic_intelligence directory if it doesn't exist
mkdir -p arctic_intelligence

echo "✅ Prerequisites checked"
echo "🚀 Starting live dashboard server..."
echo ""
echo "📊 Dashboard will be available at: http://localhost:8080/dashboard"
echo "🔄 Auto-refresh every 30 seconds"
echo "⚡ Press Ctrl+C to stop"
echo ""

# Start the live dashboard server
python3 live_dashboard_server.py
#!/bin/bash
# Activate the arcticshadowtracker_env environment

export PATH="$(pwd)/arcticshadowtracker_env/bin:$PATH"
export VIRTUAL_ENV="$(pwd)/arcticshadowtracker_env"
export PYTHONPATH="$(pwd):$PYTHONPATH"

echo "✅ ArcticShadowTracker environment activated"
echo "🐍 Python: $(which python)"
echo "📦 Python version: $(python --version)"
echo "🌊 Ready for streaming!"
echo ""
echo "💡 Usage:"
echo "   python test_stream_simple.py"
echo "   python barentswatch_stream_collector.py"
echo ""

# Start a new shell with the environment
exec "$SHELL"
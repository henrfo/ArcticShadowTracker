#!/bin/bash
# Quick script to run the streaming test

echo "🌊 Running BarentsWatch Streaming Test"
echo "=" * 40

# Use the environment Python directly
BARENTSWATCH_CLIENT_SECRET="Xw5yCEXT5gMi5PJEKEW6" ./arcticshadowtracker_env/bin/python test_stream_simple.py
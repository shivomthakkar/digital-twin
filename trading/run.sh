#!/bin/bash

# Minimal MCP Server Run Script

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Install dependencies if needed
echo "Checking dependencies..."
pip install -q -r requirements.txt

# Run the server
echo "Starting FastAPI server..."
uvicorn server:app --reload
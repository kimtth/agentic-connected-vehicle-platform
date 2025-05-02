#!/bin/bash
# Launch script for Connected Vehicle Platform

echo "Starting Connected Vehicle Platform..."

# Load environment variables from .env.azure
if [ -f .env.azure ]; then
    export $(grep -v '^#' .env.azure | xargs)
    echo "Environment variables loaded from .env.azure"
else
    echo "WARNING: .env.azure file not found"
    echo "Please run utils/azure_init.py first or create .env.azure manually"
fi

# Start the FastAPI server
echo "Starting FastAPI server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000

echo "Server is running at http://localhost:8000"

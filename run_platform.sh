#!/bin/bash

# Web Research Platform - Unified Startup Script
# Starts both the FastAPI backend and the Vite frontend.

set -e

echo "Starting Web Research Platform..."

# Ensure log directory exists before redirection
mkdir -p web_research_agent/logs

# 1. Start Backend
echo "Launching Backend API on port 8000..."
export PYTHONPATH=$PYTHONPATH:.
python3 web_research_agent/api/main.py > web_research_agent/logs/api.log 2>&1 &
BACKEND_PID=$!

# 2. Start Frontend
echo "Launching Frontend on port 5173..."
cd frontend
npm run dev -- --port 5173 > frontend.log 2>&1 &
FRONTEND_PID=$!

echo ""
echo "------------------------------------------------"
echo "Platform is running!"
echo "- Frontend: http://localhost:5173"
echo "- API:      http://localhost:8000"
echo "------------------------------------------------"
echo "Press Ctrl+C to stop all services."

# Handle shutdown
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Keep script alive
wait

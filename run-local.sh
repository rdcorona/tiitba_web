#!/bin/bash
set -e

echo "========================================"
echo "      TIITBA Web Local Runner          "
echo "========================================"

# Function to handle errors
handle_error() {
    echo ""
    echo "[ERROR] An error occurred during execution. Please check the logs above."
    exit 1
}
trap 'handle_error' ERR

# 1. Check system dependencies
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo "[ERROR] Node.js and npm are required to build the frontend."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is required."
    exit 1
fi

# 2. Frontend Setup
echo "[FRONTEND] Installing dependencies..."
cd frontend
npm install

echo "[FRONTEND] Building application to ensure latest version..."
npm run build
cd ..

# 3. Backend Setup
if [ ! -d ".venv" ]; then
    echo "[BACKEND] Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

echo "[BACKEND] Ensuring latest dependencies from requirements.txt..."
python3 -m pip install -r requirements.txt

# 4. Run App
echo ""
echo "========================================================"
echo "                 SERVER IS READY!                       "
echo "========================================================"
echo ""
echo "   1. Open your browser."
echo "   2. Go to: http://127.0.0.1:8000"
echo ""
echo "   Keep this window open to keep the server running."
echo "   Press Ctrl+C to stop the server and close."
echo "========================================================"
echo ""
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

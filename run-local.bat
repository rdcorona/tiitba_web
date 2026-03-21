@echo off
setlocal

echo ========================================
echo       TIITBA Web Local Runner          
echo ========================================

:: 1. Check system dependencies
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Node.js and npm are required to build the frontend.
    pause
    exit /b 1
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python is required.
    pause
    exit /b 1
)

:: 2. Frontend Setup
cd frontend
if not exist "node_modules\" (
    echo [FRONTEND] Installing dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install frontend dependencies.
        pause
        exit /b 1
    )
)

if not exist "dist\" (
    echo [FRONTEND] Building application...
    call npm run build
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to build the frontend.
        pause
        exit /b 1
    )
) else if "%1"=="--build" (
    echo [FRONTEND] Rebuilding application...
    call npm run build
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to build the frontend.
        pause
        exit /b 1
    )
)
cd ..

:: 3. Backend Setup
if not exist ".venv\" (
    echo [BACKEND] Creating Python virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create Python virtual environment.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Check if required packages are installed (using uvicorn as an indicator)
where uvicorn >nul 2>nul
if %errorlevel% neq 0 (
    echo [BACKEND] Installing dependencies from requirements.txt...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install backend dependencies.
        pause
        exit /b 1
    )
) else if "%1"=="--install" (
    echo [BACKEND] Updating dependencies from requirements.txt...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install backend dependencies.
        pause
        exit /b 1
    )
)

:: 4. Run App

echo.
echo ========================================================
echo                  SERVER IS READY!                       
echo ========================================================
echo.
echo    1. Open your browser.
echo    2. Go to: http://127.0.0.1:8000 for the backend API.
echo    3. Go to: http://localhost:5173 for the frontend application.
echo    Keep this window open to keep the server running.
echo    Press Ctrl+C to stop the server and close.
echo ========================================================
echo.
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause

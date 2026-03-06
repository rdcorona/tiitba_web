@echo off
setlocal

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: docker is not installed or not in PATH.
    pause
    exit /b 1
)

echo Starting TIITBA Web with Docker...
docker compose up --build -d

echo ------------------------------------------------
echo Application is starting up!
echo Visit: http://localhost:8000
echo ------------------------------------------------
echo To stop the app, run: docker compose down
pause

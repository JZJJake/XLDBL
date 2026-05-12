@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   Starting Knowledge Graph ^& Vector DB System
echo ========================================================

:: Set Hugging Face Mirror
set HF_ENDPOINT=https://hf-mirror.com

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python is not installed or not in PATH!
    pause
    goto :eof
)
echo [OK] Python found.

:: 2. Check NPM
call npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] NPM is not installed or not in PATH! Please install Node.js.
    pause
    goto :eof
)
echo [OK] NPM found.

:: 3. Setup Backend Environment and Dependencies
echo.
echo Installing Backend Dependencies (using Tsinghua mirror)...
cd backend
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
cd ..

:: 4. Setup Frontend Dependencies
echo.
echo Installing Frontend Dependencies...
cd frontend
call npm install
cd ..

:: 5. Start Services
echo.
echo ========================================================
echo   Starting Backend and Frontend Services
echo ========================================================

:: Start Backend in a new window
start "FastAPI Backend" cmd /k "set HF_ENDPOINT=https://hf-mirror.com && cd backend && title FastAPI Backend && python main.py"

:: Start Frontend in a new window
start "Vue Frontend" cmd /k "cd frontend && title Vue Frontend && npm run dev"

echo Services have been started in separate windows!
echo Backend is running on http://127.0.0.1:8000
echo Frontend is running on http://127.0.0.1:5173 (Please check the Vue Frontend window for exact URL)
echo.
pause

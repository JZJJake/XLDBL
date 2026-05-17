@echo off
echo ========================================================
echo Synthadoc Installation and Startup Script
echo ========================================================

REM Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    goto :eof
)

echo Installing dependencies...
pip install -e ".[dev]"
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies.
    pause
    goto :eof
)

echo.
echo Please enter your DeepSeek API Key:
set /p DEEPSEEK_API_KEY="API Key: "

if "%DEEPSEEK_API_KEY%"=="" (
    echo Warning: API Key is empty. You may need to provide it later.
) else (
    setx DEEPSEEK_API_KEY "%DEEPSEEK_API_KEY%"
    echo API Key saved.
)

echo.
echo Please enter a name for your default wiki (e.g. my-wiki):
set /p WIKI_NAME="Wiki Name: "
if "%WIKI_NAME%"=="" set WIKI_NAME=default-wiki

echo Installing wiki "%WIKI_NAME%"...
synthadoc install %WIKI_NAME% --target "%USERPROFILE%\wikis" --domain "Default wiki for DeepSeek"
synthadoc use %WIKI_NAME%

echo.
echo Starting Synthadoc...
synthadoc serve
pause

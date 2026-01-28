@echo off
REM ============================================================================
REM Set OpenAI API Key for Contract Analysis Tool
REM ============================================================================

echo.
echo ============================================================================
echo Contract Analysis Tool - API Key Setup
echo ============================================================================
echo.

REM Check if API key was provided as argument
if "%~1"=="" (
    echo ERROR: No API key provided
    echo.
    echo Usage: set_api_key.bat "sk-your-api-key-here"
    echo.
    echo Example:
    echo   set_api_key.bat "sk-proj-abc123..."
    echo.
    echo Get your API key from: https://platform.openai.com/api-keys
    echo.
    exit /b 1
)

REM Validate API key format (should start with sk-)
echo %~1 | findstr /B "sk-" >nul
if errorlevel 1 (
    echo ERROR: Invalid API key format
    echo.
    echo API keys should start with "sk-"
    echo.
    echo Example valid key: sk-proj-abc123...
    echo.
    exit /b 1
)

REM Set the environment variable
echo Setting OPENAI_API_KEY environment variable...
setx OPENAI_API_KEY "%~1" >nul

if errorlevel 1 (
    echo ERROR: Failed to set environment variable
    exit /b 1
)

echo.
echo ============================================================================
echo SUCCESS! API key has been set.
echo ============================================================================
echo.
echo IMPORTANT: You must restart your terminal/IDE for the change to take effect.
echo.
echo After restarting:
echo   1. Open a new terminal window
echo   2. Navigate to: %CD%
echo   3. Run: python main.py
echo.
echo ============================================================================
echo.

exit /b 0

@echo off
REM ============================================================================
REM Contract Analysis Tool - Simple Launcher
REM ============================================================================
REM This script provides an easy way to analyze contracts without the GUI
REM ============================================================================

echo ============================================================================
echo Contract Analysis Tool
echo ============================================================================
echo.

REM Check if file was provided
if "%~1"=="" (
    echo Usage: Drag and drop a PDF or DOCX file onto this batch file
    echo    or: run_contract_analysis.bat "path\to\contract.pdf"
    echo.
    echo Supported formats: .pdf, .docx
    echo.
    pause
    exit /b 1
)

REM Check if file exists
if not exist "%~1" (
    echo Error: File not found: %~1
    echo.
    pause
    exit /b 1
)

echo Processing: %~nx1
echo.
echo This may take 1-5 minutes depending on file size and type...
echo.

REM Run the analysis
python run_api_mode.py "%~1"

echo.
echo ============================================================================
echo.
pause

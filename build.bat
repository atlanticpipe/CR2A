@echo off
REM ============================================================================
REM ContractAnalysisApp PyInstaller Build Script for Windows 11
REM ============================================================================
REM This script builds a standalone executable using PyInstaller with the following features:
REM - Verifies Python 3.10+ is installed (error code 1)
REM - Installs dependencies from requirements.txt (error code 2)
REM - Builds single EXE with --noconsole --windowed --onefile flags
REM - Includes policy and schemas directories using --add-data flags
REM - PyInstaller failure handling (error code 3)
REM - Provides clear error messages and Windows 11 compatibility

setlocal enabledelayedexpansion

REM Set script variables
set "SCRIPT_NAME=%~nx0"
set "PYTHON_MIN_VERSION=3.10"
set "BUILD_NAME=ContractAnalysisApp"
set "MAIN_SCRIPT=main.py"
set "REQUIREMENTS_FILE=requirements.txt"

echo ============================================================================
echo ContractAnalysisApp Build Script Starting...
echo ============================================================================
echo.

REM ============================================================================
REM Step 1: Verify Python version (3.10+) with error code 1
REM ============================================================================
echo [1/4] Checking Python version...

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10 or higher and ensure it's in your PATH
    exit /b 1
)

REM Get Python version and check if it's >= 3.10
for /f "tokens=2 delims= " %%i in ('python --version 2^>nul') do (
    set "PYTHON_VERSION=%%i"
)

REM Extract major and minor version numbers
for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
    set "MAJOR=%%a"
    set "MINOR=%%b"
)

REM Check if version meets minimum requirements
if !MAJOR! LSS 3 (
    echo ERROR: Python version !PYTHON_VERSION! is too old
    echo Minimum required version is 3.10
    exit /b 1
)

if !MAJOR! EQU 3 (
    if !MINOR! LSS 10 (
        echo ERROR: Python version !PYTHON_VERSION! is too old
        echo Minimum required version is 3.10
        exit /b 1
    )
)

echo SUCCESS: Python !PYTHON_VERSION! detected
echo.

REM ============================================================================
REM Step 2: Install dependencies from requirements.txt with error code 2
REM ============================================================================
echo [2/4] Installing dependencies from requirements.txt...

if not exist "%REQUIREMENTS_FILE%" (
    echo ERROR: Requirements file '%REQUIREMENTS_FILE%' not found
    exit /b 2
)

pip install -r "%REQUIREMENTS_FILE%"
if errorlevel 1 (
    echo ERROR: Failed to install dependencies from %REQUIREMENTS_FILE%
    echo Please check your internet connection and requirements.txt file
    exit /b 2
)

echo SUCCESS: Dependencies installed successfully
echo.

REM ============================================================================
REM Step 3: Run PyInstaller build with error code 3
REM ============================================================================
echo [3/4] Building executable with PyInstaller...

REM Check if main script exists
if not exist "%MAIN_SCRIPT%" (
    echo ERROR: Main script '%MAIN_SCRIPT%' not found
    exit /b 3
)

REM Run PyInstaller with specified flags including --add-data for directories
pyinstaller --noconsole --windowed --onefile -n "%BUILD_NAME%" --add-data "output_schemas_v1.json;." --add-data "validation_rules_v1.json;." "%MAIN_SCRIPT%"
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    echo Check the output above for specific error details
    exit /b 3
)

echo SUCCESS: PyInstaller build completed
echo.

REM ============================================================================
REM Step 4: Verify build success
REM ============================================================================
echo [4/4] Verifying build output...

REM Check if executable was created
if exist "dist\%BUILD_NAME%.exe" (
    echo SUCCESS: Build completed successfully!
    echo.
    echo Build output location: dist\%BUILD_NAME%.exe
    echo.
    echo You can now run the executable by double-clicking:
    echo dist\%BUILD_NAME%.exe
    echo.
    echo Build process completed successfully.
    exit /b 0
) else (
    echo ERROR: Build verification failed - executable not found
    echo Expected location: dist\%BUILD_NAME%.exe
    exit /b 3
)

endlocal
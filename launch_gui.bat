@echo off
REM ============================================================================
REM CR2A GUI Launcher
REM ============================================================================
REM This script launches the CR2A Contract Analysis GUI application.
REM It performs the following operations:
REM   1. Validates that the virtual environment exists
REM   2. Validates that the GUI module is present
REM   3. Checks for API key configuration (warning only)
REM   4. Activates the Python virtual environment
REM   5. Launches the PyQt5 GUI application
REM
REM Usage: Double-click this file or run from command line
REM ============================================================================

REM ============================================================================
REM Step 1: Validate Virtual Environment
REM ============================================================================
REM Check if the Python virtual environment directory exists at the expected
REM location. The application requires venv311 to be present with all
REM necessary dependencies installed.

if not exist "venv311\" (
    echo ERROR: Virtual environment not found
    echo Expected location: venv311\
    echo.
    echo Please ensure the virtual environment is created at this location.
    echo You can create it by running: python -m venv venv311
    pause
    exit /b 1
)

REM ============================================================================
REM Step 2: Validate GUI Module
REM ============================================================================
REM Check if the GUI module file exists at the expected location.
REM The application requires src\qt_gui.py to be present to launch the GUI.

if not exist "src\qt_gui.py" (
    echo ERROR: GUI module not found
    echo Expected location: src\qt_gui.py
    echo.
    echo Please ensure the GUI module file exists at this location.
    pause
    exit /b 1
)

REM ============================================================================
REM Step 3: Check API Key Configuration
REM ============================================================================
REM Check if the OPENAI_API_KEY environment variable is set.
REM This is a non-blocking check - the GUI will launch even if the key is
REM not configured, but the user will be warned about potential issues.

if "%OPENAI_API_KEY%"=="" (
    echo WARNING: OPENAI_API_KEY environment variable is not set
    echo.
    echo The application may not function properly without an API key.
    echo Contract analysis features require a valid OpenAI API key to work.
    echo.
    echo Press any key to continue anyway...
    pause >nul
)

REM ============================================================================
REM Step 4: Activate Virtual Environment and Launch GUI
REM ============================================================================
REM Activate the Python virtual environment and execute the GUI module.
REM The activation script modifies the PATH to use the venv's Python interpreter.
REM After activation, we launch the PyQt5 GUI application.
REM
REM Set PYTHONPATH to include the project root directory so that imports work correctly.
REM This allows both "from src.module" and "from module" (when src is in path) to work.

call venv311\Scripts\activate.bat
set PYTHONPATH=%CD%
python src\qt_gui.py

REM ============================================================================
REM Exit Successfully
REM ============================================================================
REM If we reach this point, the GUI was launched successfully.
REM Exit with code 0 to indicate success.

exit /b 0

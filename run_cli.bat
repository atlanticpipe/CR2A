@echo off
REM CR2A CLI Launcher
REM Usage: run_cli.bat <contract_file_path>

if "%~1"=="" (
    echo Usage: run_cli.bat ^<contract_file_path^>
    echo Example: run_cli.bat contract.pdf
    echo.
    pause
    exit /b 1
)

echo Starting CR2A CLI Analysis...
echo File: %~1
echo.

REM Activate virtual environment if it exists
if exist venv311\Scripts\activate.bat (
    call venv311\Scripts\activate.bat
)

REM Run the CLI application
python src/cli_main.py "%~1"

if errorlevel 1 (
    echo.
    echo Error: Analysis failed
    echo Please check the file path and ensure all dependencies are installed
    pause
)

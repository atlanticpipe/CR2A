@echo off
REM CR2A Build Script
REM Rebuilds the application using PyInstaller

echo CR2A Application Builder
echo ========================
echo.

REM Activate virtual environment
if exist venv311\Scripts\activate.bat (
    call venv311\Scripts\activate.bat
) else (
    echo Error: Virtual environment not found at venv311
    pause
    exit /b 1
)

echo Building application...
echo.

REM Run the build
python -m build_tools.build_manager build all

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
) else (
    echo.
    echo Build completed successfully!
    echo Executables are in the dist/ folder
    pause
)

@echo off
REM CR2A GUI Launcher
REM Launches the PyQt5 desktop application

echo Starting CR2A GUI Application...
echo.

REM Activate virtual environment if it exists
if exist venv311\Scripts\activate.bat (
    call venv311\Scripts\activate.bat
)

REM Launch the GUI application
python src/qt_gui.py

if errorlevel 1 (
    echo.
    echo Error: Failed to launch GUI application
    echo Please ensure all dependencies are installed: pip install -r requirements.txt
    pause
)

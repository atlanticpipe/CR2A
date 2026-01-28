@echo off
REM ============================================================================
REM Contract Analysis Tool - Windows Installer Builder
REM ============================================================================
REM Creates a standalone Windows executable with PyInstaller
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================================
echo Contract Analysis Tool - Windows Installer Builder
echo ============================================================================
echo.

REM ============================================================================
REM Step 1: Check Python
REM ============================================================================
echo [1/5] Checking Python installation...

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

for /f "tokens=2 delims= " %%i in ('python --version 2^>nul') do (
    set "PYTHON_VERSION=%%i"
)

echo SUCCESS: Python !PYTHON_VERSION! detected
echo.

REM ============================================================================
REM Step 2: Install PyInstaller if needed
REM ============================================================================
echo [2/5] Checking PyInstaller...

python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        exit /b 2
    )
)

echo SUCCESS: PyInstaller is ready
echo.

REM ============================================================================
REM Step 3: Clean previous builds
REM ============================================================================
echo [3/5] Cleaning previous builds...

if exist "build" (
    echo Removing build directory...
    rd /s /q build
)

if exist "dist" (
    echo Removing dist directory...
    rd /s /q dist
)

if exist "ContractAnalysisApp.spec" (
    echo Removing old spec file...
    del ContractAnalysisApp.spec
)

echo SUCCESS: Build directories cleaned
echo.

REM ============================================================================
REM Step 4: Build executable with PyInstaller
REM ============================================================================
echo [4/5] Building executable with PyInstaller...
echo This may take 2-3 minutes...
echo.

REM Build with PyInstaller
python -m PyInstaller ^
    --name="ContractAnalysisApp" ^
    --onefile ^
    --windowed ^
    --add-data="output_schemas_v1.json;." ^
    --add-data="validation_rules_v1.json;." ^
    --hidden-import=pytesseract ^
    --hidden-import=pdf2image ^
    --hidden-import=PIL ^
    --hidden-import=pdfminer ^
    --hidden-import=docx ^
    --hidden-import=reportlab ^
    --hidden-import=PySimpleGUI ^
    --hidden-import=openai ^
    --hidden-import=jsonschema ^
    main.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    exit /b 3
)

echo.
echo SUCCESS: Executable built successfully
echo.

REM ============================================================================
REM Step 5: Verify and package
REM ============================================================================
echo [5/5] Verifying build...

if not exist "dist\ContractAnalysisApp.exe" (
    echo ERROR: Executable not found at dist\ContractAnalysisApp.exe
    exit /b 4
)

for %%A in ("dist\ContractAnalysisApp.exe") do (
    set "FILE_SIZE=%%~zA"
)

echo SUCCESS: Executable created successfully!
echo Location: dist\ContractAnalysisApp.exe
echo Size: !FILE_SIZE! bytes
echo.

REM Create a simple distribution package
echo Creating distribution package...

if not exist "release" mkdir release

copy "dist\ContractAnalysisApp.exe" "release\" >nul
copy "README.md" "release\README.txt" >nul
copy "API_KEY_SETUP.md" "release\API_KEY_SETUP.txt" >nul
copy "OCR_SETUP_GUIDE.md" "release\OCR_SETUP_GUIDE.txt" >nul

REM Create a quick start guide
echo Creating Quick Start guide...
(
echo Contract Analysis Tool - Quick Start
echo =====================================
echo.
echo IMPORTANT: Before running the application, you need:
echo.
echo 1. OpenAI API Key
echo    - Get from: https://platform.openai.com/api-keys
echo    - Set environment variable: OPENAI_API_KEY
echo.
echo 2. Tesseract OCR ^(for scanned PDFs^)
echo    - Download: https://github.com/UB-Mannheim/tesseract/wiki
echo    - Install and add to PATH
echo.
echo 3. Poppler ^(for scanned PDFs^)
echo    - Included in OCR_SETUP_GUIDE.txt
echo.
echo USAGE:
echo ------
echo 1. Double-click ContractAnalysisApp.exe
echo 2. Drag and drop a PDF or DOCX contract file
echo 3. Wait for analysis to complete
echo 4. Review the generated report
echo.
echo For detailed setup instructions, see:
echo - API_KEY_SETUP.txt
echo - OCR_SETUP_GUIDE.txt
echo - README.txt
echo.
echo TROUBLESHOOTING:
echo ----------------
echo - If API key error: Set OPENAI_API_KEY environment variable
echo - If OCR fails: Install Tesseract and Poppler
echo - Check error.log for detailed error messages
echo.
) > "release\QUICK_START.txt"

echo.
echo ============================================================================
echo BUILD COMPLETED SUCCESSFULLY!
echo ============================================================================
echo.
echo Executable Location: dist\ContractAnalysisApp.exe
echo Distribution Package: release\
echo.
echo Distribution Package Contents:
echo   - ContractAnalysisApp.exe  (Main application)
echo   - README.txt               (Full documentation)
echo   - QUICK_START.txt          (Quick setup guide)
echo   - API_KEY_SETUP.txt        (API key configuration)
echo   - OCR_SETUP_GUIDE.txt      (OCR installation guide)
echo.
echo NEXT STEPS:
echo -----------
echo 1. Test the executable: dist\ContractAnalysisApp.exe
echo 2. Distribute the release\ folder to users
echo 3. Users must set OPENAI_API_KEY before first use
echo 4. Users must install Tesseract OCR for scanned PDFs
echo.
echo NOTES:
echo ------
echo - The .exe is portable and self-contained
echo - No Python installation required on target machines
echo - Tesseract and Poppler must be installed separately
echo - API key must be set as environment variable
echo.
echo ============================================================================
echo.

pause
endlocal

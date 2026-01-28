@echo off
REM ============================================================================
REM Contract Analysis Tool - CLI Version Builder
REM ============================================================================
REM Builds a command-line version without GUI dependencies
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================================
echo Contract Analysis Tool - CLI Version Builder
echo ============================================================================
echo.

REM ============================================================================
REM Step 1: Check Python
REM ============================================================================
echo [1/4] Checking Python installation...

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
REM Step 2: Clean previous builds
REM ============================================================================
echo [2/4] Cleaning previous builds...

if exist "build" (
    echo Removing build directory...
    rd /s /q build
)

if exist "dist" (
    echo Removing dist directory...
    rd /s /q dist
)

if exist "ContractAnalysisCLI.spec" (
    echo Removing old spec file...
    del ContractAnalysisCLI.spec
)

echo SUCCESS: Build directories cleaned
echo.

REM ============================================================================
REM Step 3: Build CLI executable with PyInstaller
REM ============================================================================
echo [3/4] Building CLI executable with PyInstaller...
echo This may take 2-3 minutes...
echo.

REM Build with PyInstaller - CLI version using run_api_mode.py
python -m PyInstaller ^
    --name="ContractAnalysisCLI" ^
    --onefile ^
    --console ^
    --add-data="output_schemas_v1.json;." ^
    --add-data="validation_rules_v1.json;." ^
    --hidden-import=pytesseract ^
    --hidden-import=pdf2image ^
    --hidden-import=PIL ^
    --hidden-import=pdfminer ^
    --hidden-import=docx ^
    --hidden-import=reportlab ^
    --hidden-import=openai ^
    --hidden-import=jsonschema ^
    --exclude-module=PySimpleGUI ^
    --exclude-module=gui ^
    run_api_mode.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    exit /b 3
)

echo.
echo SUCCESS: Executable built successfully
echo.

REM ============================================================================
REM Step 4: Verify and package
REM ============================================================================
echo [4/4] Verifying build...

if not exist "dist\ContractAnalysisCLI.exe" (
    echo ERROR: Executable not found at dist\ContractAnalysisCLI.exe
    exit /b 4
)

for %%A in ("dist\ContractAnalysisCLI.exe") do (
    set "FILE_SIZE=%%~zA"
)

echo SUCCESS: Executable created successfully!
echo Location: dist\ContractAnalysisCLI.exe
echo Size: !FILE_SIZE! bytes
echo.

REM Create a simple distribution package
echo Creating distribution package...

if not exist "release_cli" mkdir release_cli

copy "dist\ContractAnalysisCLI.exe" "release_cli\" >nul
copy "README.md" "release_cli\README.txt" >nul
copy "API_KEY_SETUP.md" "release_cli\API_KEY_SETUP.txt" >nul
copy "OCR_SETUP_GUIDE.md" "release_cli\OCR_SETUP_GUIDE.txt" >nul

REM Create a usage guide
echo Creating usage guide...
(
echo Contract Analysis Tool - CLI Version
echo ====================================
echo.
echo USAGE:
echo ------
echo.
echo Method 1: Command Line
echo   ContractAnalysisCLI.exe "path\to\contract.pdf"
echo.
echo Method 2: Drag and Drop
echo   Drag a PDF or DOCX file onto ContractAnalysisCLI.exe
echo.
echo REQUIREMENTS:
echo -------------
echo 1. OpenAI API Key ^(required^)
echo    - Set environment variable: OPENAI_API_KEY
echo    - See API_KEY_SETUP.txt for instructions
echo.
echo 2. Tesseract OCR ^(optional, for scanned PDFs^)
echo    - See OCR_SETUP_GUIDE.txt for installation
echo.
echo 3. Poppler ^(optional, for scanned PDFs^)
echo    - See OCR_SETUP_GUIDE.txt for installation
echo.
echo OUTPUT:
echo -------
echo - [filename]_analysis.json  ^(structured data^)
echo - [filename]_analysis.pdf   ^(professional report^)
echo.
echo Both files are saved in the same folder as the input file.
echo.
echo EXAMPLES:
echo ---------
echo   ContractAnalysisCLI.exe "C:\Documents\Contract.pdf"
echo   ContractAnalysisCLI.exe "Service Agreement.docx"
echo.
echo TROUBLESHOOTING:
echo ----------------
echo - If API key error: Set OPENAI_API_KEY environment variable
echo - If OCR fails: Install Tesseract and Poppler
echo - Check error.log for detailed error messages
echo.
echo For detailed setup instructions, see:
echo - API_KEY_SETUP.txt
echo - OCR_SETUP_GUIDE.txt
echo - README.txt
echo.
) > "release_cli\USAGE.txt"

echo.
echo ============================================================================
echo BUILD COMPLETED SUCCESSFULLY!
echo ============================================================================
echo.
echo CLI Executable Location: dist\ContractAnalysisCLI.exe
echo Distribution Package: release_cli\
echo.
echo Distribution Package Contents:
echo   - ContractAnalysisCLI.exe  (Main CLI application)
echo   - USAGE.txt                (Usage instructions)
echo   - README.txt               (Full documentation)
echo   - API_KEY_SETUP.txt        (API key configuration)
echo   - OCR_SETUP_GUIDE.txt      (OCR installation guide)
echo.
echo USAGE:
echo ------
echo   ContractAnalysisCLI.exe "Contract #1.pdf"
echo.
echo   or drag and drop a file onto the .exe
echo.
echo NOTES:
echo ------
echo - This is a command-line version (no GUI)
echo - Shows progress in console window
echo - Easier to troubleshoot than GUI version
echo - Same functionality as GUI version
echo.
echo ============================================================================
echo.

pause
endlocal

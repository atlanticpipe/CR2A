@echo off
REM Build script for Contract Analysis CLI (Drag & Drop)
REM Creates a standalone executable that accepts files via drag & drop

echo ========================================
echo Building Contract Analysis CLI
echo ========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist\ContractAnalysisCLI.exe" del /q "dist\ContractAnalysisCLI.exe"

echo.
echo Building executable...
echo This may take 2-3 minutes...
echo.

REM Build the executable
pyinstaller --onefile ^
    --console ^
    --name ContractAnalysisCLI ^
    --add-data "output_schemas_v1.json;." ^
    --add-data "validation_rules_v1.json;." ^
    --hidden-import=pytesseract ^
    --hidden-import=pdf2image ^
    --hidden-import=PIL ^
    --hidden-import=PIL.Image ^
    --hidden-import=pdfminer ^
    --hidden-import=pdfminer.high_level ^
    --hidden-import=pdfminer.layout ^
    --hidden-import=docx ^
    --hidden-import=openai ^
    --hidden-import=jsonschema ^
    --collect-all pdfminer ^
    contract_analysis_cli.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo BUILD FAILED!
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo Executable location: dist\ContractAnalysisCLI.exe
echo File size: 
dir /b dist\ContractAnalysisCLI.exe | findstr /v "^$"
for %%A in (dist\ContractAnalysisCLI.exe) do echo %%~zA bytes

echo.
echo USAGE:
echo   1. Drag and drop a contract file onto ContractAnalysisCLI.exe
echo   2. Or run from command line: ContractAnalysisCLI.exe contract.pdf
echo.
echo REQUIREMENTS:
echo   - OpenAI API key set as environment variable OPENAI_API_KEY
echo   - For scanned PDFs: Tesseract OCR and Poppler installed
echo.
echo Cleaning up build artifacts...
rmdir /s /q build
del /q ContractAnalysisCLI.spec

echo.
echo Done! The executable is ready to use.
echo.
pause

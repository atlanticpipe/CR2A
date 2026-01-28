@echo off
REM ============================================================================
REM Repository Cleanup Script
REM Removes build artifacts, temporary files, and organizes the repository
REM ============================================================================

echo ============================================================================
echo Repository Cleanup
echo ============================================================================
echo.

REM Remove build artifacts
echo Cleaning build artifacts...
if exist "build" rd /s /q build
if exist "__pycache__" rd /s /q __pycache__
if exist "*.pyc" del /s /q *.pyc
if exist "*.pyo" del /s /q *.pyo
if exist "*.spec" del /q *.spec

REM Remove old documentation files that are now consolidated
echo Removing redundant documentation...
if exist "CLEANUP_COMPLETED.md" del /q CLEANUP_COMPLETED.md
if exist "OCR_IMPLEMENTATION_COMPLETE.md" del /q OCR_IMPLEMENTATION_COMPLETE.md
if exist "PDF_ISSUE_REPORT.md" del /q PDF_ISSUE_REPORT.md

REM Remove test/temporary files
echo Removing test files...
if exist "test_extraction.py" del /q test_extraction.py
if exist "check_pdf_type.py" del /q check_pdf_type.py
if exist "validate_fixes.py" del /q validate_fixes.py
if exist "build_verification.py" del /q build_verification.py
if exist "error.log" del /q error.log

REM Remove old installer scripts (keeping only the new one)
echo Cleaning old installer scripts...
if exist "installers\create_installer.bat" del /q installers\create_installer.bat
if exist "installers\create_selfcontained_installer.bat" del /q installers\create_selfcontained_installer.bat
if exist "installers\manual_installer.bat" del /q installers\manual_installer.bat
if exist "installers\setup_selfcontained_installer.bat" del /q installers\setup_selfcontained_installer.bat
if exist "installers\installer.nsi" del /q installers\installer.nsi

REM Remove old setup scripts (consolidated into new ones)
echo Removing old setup scripts...
if exist "install_tesseract_now.bat" del /q install_tesseract_now.bat
if exist "run_contract_analyzer.bat" del /q run_contract_analyzer.bat
if exist "launch_web_analyzer.bat" del /q launch_web_analyzer.bat
if exist "start_api_server.sh" del /q start_api_server.sh

REM Keep only essential batch files
echo Organizing scripts...

echo.
echo ============================================================================
echo Cleanup Complete!
echo ============================================================================
echo.
echo Removed:
echo   - Build artifacts (build/, __pycache__/, *.pyc)
echo   - Redundant documentation files
echo   - Old test scripts
echo   - Obsolete installer scripts
echo   - Temporary files
echo.
echo Kept:
echo   - Source code (*.py)
echo   - Essential documentation (README.md, FINAL_STATUS.md, etc.)
echo   - Distribution package (release/)
echo   - Executable (dist/ContractAnalysisApp.exe)
echo   - Configuration files (*.json, requirements.txt)
echo   - Setup scripts (set_api_key.*, install_*.ps1)
echo.
echo ============================================================================
echo.
pause

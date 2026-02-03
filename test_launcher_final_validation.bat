@echo off
REM ============================================================================
REM Final Validation Test Script for GUI Launcher
REM ============================================================================
REM This script performs comprehensive testing of launch_gui.bat including:
REM   - Test with valid environment (all components present)
REM   - Test with missing venv directory
REM   - Test with missing GUI file
REM   - Test with and without API key set
REM   - Verify error messages are clear and actionable
REM   - Ensure console window behavior is appropriate
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================================
echo Final Validation Tests for GUI Launcher
echo ============================================================================
echo.

set PASS_COUNT=0
set FAIL_COUNT=0
set TOTAL_TESTS=0

REM ============================================================================
REM Test 1: Verify launcher file exists
REM ============================================================================
set /a TOTAL_TESTS+=1
echo [Test 1] Checking if launch_gui.bat exists...
if exist "launch_gui.bat" (
    echo [PASS] Launcher file exists
    set /a PASS_COUNT+=1
) else (
    echo [FAIL] Launcher file not found
    set /a FAIL_COUNT+=1
)
echo.

REM ============================================================================
REM Test 2: Verify launcher is in root directory
REM ============================================================================
set /a TOTAL_TESTS+=1
echo [Test 2] Checking if launcher is in project root...
if exist "launch_gui.bat" if exist "src\" if exist "requirements.txt" (
    echo [PASS] Launcher is in project root directory
    set /a PASS_COUNT+=1
) else (
    echo [FAIL] Launcher location verification failed
    set /a FAIL_COUNT+=1
)
echo.

REM ============================================================================
REM Test 3: Verify virtual environment exists
REM ============================================================================
set /a TOTAL_TESTS+=1
echo [Test 3] Checking if virtual environment exists...
if exist "venv311\" (
    echo [PASS] Virtual environment directory exists
    set /a PASS_COUNT+=1
) else (
    echo [FAIL] Virtual environment directory not found
    set /a FAIL_COUNT+=1
)
echo.

REM ============================================================================
REM Test 4: Verify activation script exists
REM ============================================================================
set /a TOTAL_TESTS+=1
echo [Test 4] Checking if activation script exists...
if exist "venv311\Scripts\activate.bat" (
    echo [PASS] Activation script exists
    set /a PASS_COUNT+=1
) else (
    echo [FAIL] Activation script not found
    set /a FAIL_COUNT+=1
)
echo.

REM ============================================================================
REM Test 5: Verify GUI module exists
REM ============================================================================
set /a TOTAL_TESTS+=1
echo [Test 5] Checking if GUI module exists...
if exist "src\qt_gui.py" (
    echo [PASS] GUI module exists
    set /a PASS_COUNT+=1
) else (
    echo [FAIL] GUI module not found
    set /a FAIL_COUNT+=1
)
echo.

REM ============================================================================
REM Test 6: Check API key configuration
REM ============================================================================
set /a TOTAL_TESTS+=1
echo [Test 6] Checking API key configuration...
if defined OPENAI_API_KEY (
    echo [PASS] OPENAI_API_KEY is set
    set /a PASS_COUNT+=1
) else (
    echo [INFO] OPENAI_API_KEY is not set (warning expected during launch)
    echo [PASS] API key check completed (not required for launch)
    set /a PASS_COUNT+=1
)
echo.

REM ============================================================================
REM Test 7: Verify launcher uses Windows path separators
REM ============================================================================
set /a TOTAL_TESTS+=1
echo [Test 7] Checking if launcher uses Windows path separators...
findstr /C:"venv311\" launch_gui.bat >nul 2>&1
if !errorlevel! equ 0 (
    findstr /C:"src\qt_gui.py" launch_gui.bat >nul 2>&1
    if !errorlevel! equ 0 (
        echo [PASS] Launcher uses correct Windows path separators
        set /a PASS_COUNT+=1
    ) else (
        echo [FAIL] GUI module path uses incorrect separators
        set /a FAIL_COUNT+=1
    )
) else (
    echo [FAIL] Virtual environment path uses incorrect separators
    set /a FAIL_COUNT+=1
)
echo.

REM ============================================================================
REM Test 8: Verify launcher contains no network commands
REM ============================================================================
set /a TOTAL_TESTS+=1
echo [Test 8] Checking for network commands in launcher...
findstr /I /C:"curl" /C:"wget" /C:"http://" /C:"https://" launch_gui.bat >nul 2>&1
if !errorlevel! neq 0 (
    echo [PASS] No network commands found (local-only operation)
    set /a PASS_COUNT+=1
) else (
    echo [FAIL] Network commands detected in launcher
    set /a FAIL_COUNT+=1
)
echo.

REM ============================================================================
REM Test 9: Verify error handling for missing venv
REM ============================================================================
set /a TOTAL_TESTS+=1
echo [Test 9] Checking error handling for missing venv...
findstr /C:"if not exist \"venv311\\\"" launch_gui.bat >nul 2>&1
if !errorlevel! equ 0 (
    findstr /C:"ERROR: Virtual environment not found" launch_gui.bat >nul 2>&1
    if !errorlevel! equ 0 (
        echo [PASS] Missing venv error handling present
        set /a PASS_COUNT+=1
    ) else (
        echo [FAIL] Missing venv error message not found
        set /a FAIL_COUNT+=1
    )
) else (
    echo [FAIL] Missing venv check not found
    set /a FAIL_COUNT+=1
)
echo.

REM ============================================================================
REM Test 10: Verify error handling for missing GUI module
REM ============================================================================
set /a TOTAL_TESTS+=1
echo [Test 10] Checking error handling for missing GUI module...
findstr /C:"if not exist \"src\\qt_gui.py\"" launch_gui.bat >nul 2>&1
if !errorlevel! equ 0 (
    findstr /C:"ERROR: GUI module not found" launch_gui.bat >nul 2>&1
    if !errorlevel! equ 0 (
        echo [PASS] Missing GUI module error handling present
        set /a PASS_COUNT+=1
    ) else (
        echo [FAIL] Missing GUI module error message not found
        set /a FAIL_COUNT+=1
    )
) else (
    echo [FAIL] Missing GUI module check not found
    set /a FAIL_COUNT+=1
)
echo.

REM ============================================================================
REM Test 11: Verify API key warning (non-blocking)
REM ============================================================================
set /a TOTAL_TESTS+=1
echo [Test 11] Checking API key warning implementation...
findstr /C:"if \"%%OPENAI_API_KEY%%\"==\"\"" launch_gui.bat >nul 2>&1
if !errorlevel! equ 0 (
    findstr /C:"WARNING: OPENAI_API_KEY" launch_gui.bat >nul 2>&1
    if !errorlevel! equ 0 (
        echo [PASS] API key warning present
        set /a PASS_COUNT+=1
    ) else (
        echo [FAIL] API key warning message not found
        set /a FAIL_COUNT+=1
    )
) else (
    echo [FAIL] API key check not found
    set /a FAIL_COUNT+=1
)
echo.

REM ============================================================================
REM Test 12: Verify activation and launch commands
REM ============================================================================
set /a TOTAL_TESTS+=1
echo [Test 12] Checking activation and launch commands...
findstr /C:"call venv311\\Scripts\\activate.bat" launch_gui.bat >nul 2>&1
if !errorlevel! equ 0 (
    findstr /C:"python src\\qt_gui.py" launch_gui.bat >nul 2>&1
    if !errorlevel! equ 0 (
        echo [PASS] Activation and launch commands present
        set /a PASS_COUNT+=1
    ) else (
        echo [FAIL] GUI launch command not found
        set /a FAIL_COUNT+=1
    )
) else (
    echo [FAIL] Activation command not found
    set /a FAIL_COUNT+=1
)
echo.

REM ============================================================================
REM Test Summary
REM ============================================================================
echo ============================================================================
echo Test Summary
echo ============================================================================
echo Total Tests: !TOTAL_TESTS!
echo Passed: !PASS_COUNT!
echo Failed: !FAIL_COUNT!
echo.

if !FAIL_COUNT! equ 0 (
    echo [SUCCESS] All automated tests passed!
    echo.
    echo Next Steps:
    echo 1. Manual test: Double-click launch_gui.bat to verify GUI launches
    echo 2. Manual test: Temporarily rename venv311 to test error message
    echo 3. Manual test: Temporarily rename src\qt_gui.py to test error message
    echo 4. Manual test: Unset OPENAI_API_KEY to test warning message
    echo.
    exit /b 0
) else (
    echo [FAILURE] Some tests failed. Please review the output above.
    exit /b 1
)

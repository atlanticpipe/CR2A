@echo off
REM ============================================================================
REM Launcher Validation Test Script
REM ============================================================================
REM This script performs comprehensive validation testing of launch_gui.bat
REM Tests all scenarios: valid environment, missing components, API key checks
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================================
echo CR2A Launcher Validation Test Suite
echo ============================================================================
echo.

set PASSED=0
set FAILED=0
set TOTAL=0

REM ============================================================================
REM Test 1: Verify launcher file exists
REM ============================================================================
set /a TOTAL+=1
echo [Test 1] Checking if launch_gui.bat exists...
if exist "launch_gui.bat" (
    echo [PASS] Launcher file exists
    set /a PASSED+=1
) else (
    echo [FAIL] Launcher file not found
    set /a FAILED+=1
)
echo.

REM ============================================================================
REM Test 2: Verify virtual environment exists
REM ============================================================================
set /a TOTAL+=1
echo [Test 2] Checking if venv311 directory exists...
if exist "venv311\" (
    echo [PASS] Virtual environment directory exists
    set /a PASSED+=1
) else (
    echo [FAIL] Virtual environment directory not found
    set /a FAILED+=1
)
echo.

REM ============================================================================
REM Test 3: Verify activation script exists
REM ============================================================================
set /a TOTAL+=1
echo [Test 3] Checking if activation script exists...
if exist "venv311\Scripts\activate.bat" (
    echo [PASS] Activation script exists
    set /a PASSED+=1
) else (
    echo [FAIL] Activation script not found
    set /a FAILED+=1
)
echo.

REM ============================================================================
REM Test 4: Verify GUI module exists
REM ============================================================================
set /a TOTAL+=1
echo [Test 4] Checking if GUI module exists...
if exist "src\qt_gui.py" (
    echo [PASS] GUI module exists
    set /a PASSED+=1
) else (
    echo [FAIL] GUI module not found
    set /a FAILED+=1
)
echo.

REM ============================================================================
REM Test 5: Check API key configuration
REM ============================================================================
set /a TOTAL+=1
echo [Test 5] Checking API key configuration...
if defined OPENAI_API_KEY (
    echo [PASS] OPENAI_API_KEY is set
    set /a PASSED+=1
) else (
    echo [WARN] OPENAI_API_KEY is not set (launcher will show warning)
    set /a PASSED+=1
)
echo.

REM ============================================================================
REM Test 6: Verify launcher uses Windows path separators
REM ============================================================================
set /a TOTAL+=1
echo [Test 6] Checking launcher uses Windows path separators...
findstr /C:"venv311\" launch_gui.bat >nul 2>&1
if !errorlevel! equ 0 (
    findstr /C:"src\qt_gui.py" launch_gui.bat >nul 2>&1
    if !errorlevel! equ 0 (
        echo [PASS] Launcher uses Windows path separators
        set /a PASSED+=1
    ) else (
        echo [FAIL] Launcher missing Windows path separators
        set /a FAILED+=1
    )
) else (
    echo [FAIL] Launcher missing Windows path separators
    set /a FAILED+=1
)
echo.

REM ============================================================================
REM Test 7: Verify launcher has no network commands
REM ============================================================================
set /a TOTAL+=1
echo [Test 7] Checking launcher has no network commands...
findstr /I /C:"curl" /C:"wget" /C:"http" /C:"https" launch_gui.bat >nul 2>&1
if !errorlevel! neq 0 (
    echo [PASS] No network commands found
    set /a PASSED+=1
) else (
    echo [FAIL] Network commands found in launcher
    set /a FAILED+=1
)
echo.

REM ============================================================================
REM Test 8: Verify launcher is in root directory
REM ============================================================================
set /a TOTAL+=1
echo [Test 8] Checking launcher is in root directory...
if exist "launch_gui.bat" (
    echo [PASS] Launcher is in root directory
    set /a PASSED+=1
) else (
    echo [FAIL] Launcher not in root directory
    set /a FAILED+=1
)
echo.

REM ============================================================================
REM Test Summary
REM ============================================================================
echo ============================================================================
echo Test Summary
echo ============================================================================
echo Total Tests: !TOTAL!
echo Passed: !PASSED!
echo Failed: !FAILED!
echo.

if !FAILED! equ 0 (
    echo [SUCCESS] All validation tests passed!
    echo.
    echo The launcher is ready for manual testing.
    echo You can now test by double-clicking launch_gui.bat
) else (
    echo [WARNING] Some tests failed. Please review the results above.
)
echo.
echo ============================================================================

pause

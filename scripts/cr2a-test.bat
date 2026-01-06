@echo off
REM CR2A Testing Framework CLI Wrapper Script for Windows
REM Provides convenient shortcuts for common testing operations

setlocal enabledelayedexpansion

REM Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "CLI_SCRIPT=%SCRIPT_DIR%cr2a_test_cli.py"

REM Function to print colored output (basic version for Windows)
goto :main

:print_status
echo %~2
goto :eof

:check_cli_script
if not exist "%CLI_SCRIPT%" (
    echo Error: CLI script not found at %CLI_SCRIPT%
    exit /b 1
)
goto :eof

:check_python_env
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8 or later.
    exit /b 1
)

python -c "import boto3" >nul 2>&1
if errorlevel 1 (
    echo Warning: boto3 not found. You may need to activate a virtual environment or install dependencies.
    echo Run: pip install -r requirements.txt
)
goto :eof

:show_usage
echo CR2A Testing Framework CLI
echo.
echo Usage: %~nx0 ^<command^> [options]
echo.
echo Commands:
echo   test ^<phase^>              Run tests (component^|integration^|all)
echo   deploy ^<resource^>         Deploy resources (lambda^|layers)
echo   setup ^<target^>            Set up AWS resources (aws)
echo   validate [component]      Validate setup (iam^|logs^|lambda^|stepfunctions^|apigateway^|all)
echo   report                    Generate test report
echo   layers ^<action^>           Manage Lambda layers (create^|list^|cleanup)
echo   config ^<action^>           Manage configuration (create^|show^|validate)
echo.
echo Quick Commands:
echo   quick-test               Run all tests with verbose output
echo   quick-setup              Set up all AWS resources and deploy Lambda functions
echo   quick-validate           Validate entire setup
echo   status                   Show current system status
echo.
echo Options:
echo   --region ^<region^>        AWS region (default: us-east-1)
echo   --config ^<file^>          Configuration file path
echo   --verbose                Verbose output
echo   --help                   Show detailed help
echo.
echo Examples:
echo   %~nx0 quick-test                    # Run all tests
echo   %~nx0 test component --verbose      # Run component tests with verbose output
echo   %~nx0 deploy lambda                 # Deploy Lambda test functions
echo   %~nx0 setup aws --resource all     # Set up all AWS resources
echo   %~nx0 validate --verbose           # Validate setup with detailed output
echo   %~nx0 config create                 # Create sample configuration file
echo.
echo For detailed help on any command:
echo   %~nx0 ^<command^> --help
goto :eof

:quick_test
echo 🚀 Running CR2A Quick Test...
python "%CLI_SCRIPT%" test all --verbose --generate-report %*
goto :eof

:quick_setup
echo 🔧 Running CR2A Quick Setup...

echo Step 1: Setting up AWS resources...
python "%CLI_SCRIPT%" setup aws --resource all %*

echo Step 2: Deploying Lambda functions...
python "%CLI_SCRIPT%" deploy lambda %*

echo Step 3: Validating setup...
python "%CLI_SCRIPT%" validate --component all %*

echo ✅ Quick setup completed!
goto :eof

:quick_validate
echo 🔍 Running CR2A Quick Validation...
python "%CLI_SCRIPT%" validate --component all --verbose %*
goto :eof

:show_status
echo 📊 CR2A System Status
echo.

echo Validating AWS Setup...
python "%CLI_SCRIPT%" validate --component all %*

echo.
echo Configuration:
python "%SCRIPT_DIR%config_manager.py" show %*
goto :eof

:main
REM Check prerequisites
call :check_cli_script
if errorlevel 1 exit /b 1

call :check_python_env
if errorlevel 1 exit /b 1

REM Change to project root directory
cd /d "%PROJECT_ROOT%"

REM Handle commands
set "COMMAND=%~1"

if "%COMMAND%"=="test" (
    shift
    python "%CLI_SCRIPT%" test %*
) else if "%COMMAND%"=="deploy" (
    shift
    python "%CLI_SCRIPT%" deploy %*
) else if "%COMMAND%"=="setup" (
    shift
    python "%CLI_SCRIPT%" setup %*
) else if "%COMMAND%"=="validate" (
    shift
    python "%CLI_SCRIPT%" validate %*
) else if "%COMMAND%"=="report" (
    shift
    python "%CLI_SCRIPT%" report %*
) else if "%COMMAND%"=="layers" (
    shift
    python "%CLI_SCRIPT%" layers %*
) else if "%COMMAND%"=="config" (
    shift
    python "%SCRIPT_DIR%config_manager.py" %*
) else if "%COMMAND%"=="quick-test" (
    shift
    call :quick_test %*
) else if "%COMMAND%"=="quick-setup" (
    shift
    call :quick_setup %*
) else if "%COMMAND%"=="quick-validate" (
    shift
    call :quick_validate %*
) else if "%COMMAND%"=="status" (
    shift
    call :show_status %*
) else if "%COMMAND%"=="--help" (
    call :show_usage
) else if "%COMMAND%"=="-h" (
    call :show_usage
) else if "%COMMAND%"=="help" (
    call :show_usage
) else if "%COMMAND%"=="" (
    echo Error: No command specified
    echo.
    call :show_usage
    exit /b 1
) else (
    echo Error: Unknown command '%COMMAND%'
    echo.
    call :show_usage
    exit /b 1
)

endlocal
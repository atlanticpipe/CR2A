@echo off
REM Quick OCR Test Script
REM Tests OCR extraction on Contract #1.pdf

echo ======================================================================
echo OCR Test - Contract Analysis Tool
echo ======================================================================
echo.

echo Testing OCR extraction on Contract #1.pdf...
echo This will take 2-3 minutes for 15 pages.
echo.

python extract.py "Contract #1.pdf"

echo.
echo ======================================================================
echo Test Complete!
echo ======================================================================
echo.
echo If you see "Successfully extracted text" above, OCR is working!
echo.
echo Next step: Fix your OpenAI API key and run:
echo   python run_api_mode.py "Contract #1.pdf"
echo.
pause

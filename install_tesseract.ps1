# ============================================================================
# Tesseract OCR Installation Script for Windows
# ============================================================================

Write-Host ""
Write-Host "============================================================================"
Write-Host "Tesseract OCR Installation for Contract Analysis Tool"
Write-Host "============================================================================"
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  This script should be run as Administrator for best results." -ForegroundColor Yellow
    Write-Host "   Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
}

# Check if Tesseract is already installed
Write-Host "Checking for existing Tesseract installation..."
$tesseractPath = $null

# Common installation paths
$commonPaths = @(
    "C:\Program Files\Tesseract-OCR\tesseract.exe",
    "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "$env:LOCALAPPDATA\Programs\Tesseract-OCR\tesseract.exe"
)

foreach ($path in $commonPaths) {
    if (Test-Path $path) {
        $tesseractPath = $path
        break
    }
}

if ($tesseractPath) {
    Write-Host "✓ Tesseract is already installed at: $tesseractPath" -ForegroundColor Green
    
    # Check if it's in PATH
    $inPath = $env:Path -split ';' | Where-Object { Test-Path "$_\tesseract.exe" }
    
    if ($inPath) {
        Write-Host "✓ Tesseract is in PATH" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Tesseract is not in PATH" -ForegroundColor Yellow
        $tesseractDir = Split-Path $tesseractPath
        Write-Host "   Adding to PATH: $tesseractDir" -ForegroundColor Yellow
        
        # Add to user PATH
        $currentPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
        if ($currentPath -notlike "*$tesseractDir*") {
            [System.Environment]::SetEnvironmentVariable("Path", "$currentPath;$tesseractDir", "User")
            $env:Path += ";$tesseractDir"
            Write-Host "✓ Added to PATH" -ForegroundColor Green
        }
    }
    
    # Test Tesseract
    try {
        $version = & $tesseractPath --version 2>&1 | Select-Object -First 1
        Write-Host "✓ Tesseract version: $version" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Could not get Tesseract version" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "============================================================================"
    Write-Host "✓ Tesseract OCR is ready to use!" -ForegroundColor Green
    Write-Host "============================================================================"
    Write-Host ""
    Write-Host "You can now use OCR in the Contract Analysis Tool."
    Write-Host ""
    Write-Host "Test it with:"
    Write-Host "  python run_api_mode.py 'Contract #1.pdf'" -ForegroundColor Cyan
    Write-Host ""
    
} else {
    Write-Host "✗ Tesseract is not installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "============================================================================"
    Write-Host "Installation Instructions"
    Write-Host "============================================================================"
    Write-Host ""
    Write-Host "Option 1: Download and Install Manually (Recommended)"
    Write-Host "------------------------------------------------------"
    Write-Host "1. Download Tesseract installer from:"
    Write-Host "   https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "2. Download the latest version (e.g., tesseract-ocr-w64-setup-5.3.3.exe)"
    Write-Host ""
    Write-Host "3. Run the installer"
    Write-Host "   - Install to: C:\Program Files\Tesseract-OCR"
    Write-Host "   - Select 'Add to PATH' during installation"
    Write-Host ""
    Write-Host "4. Restart your terminal/IDE"
    Write-Host ""
    Write-Host "5. Verify installation:"
    Write-Host "   tesseract --version" -ForegroundColor Cyan
    Write-Host ""
    Write-Host ""
    Write-Host "Option 2: Use Chocolatey (If you have it installed)"
    Write-Host "----------------------------------------------------"
    Write-Host "choco install tesseract" -ForegroundColor Cyan
    Write-Host ""
    Write-Host ""
    Write-Host "Option 3: Use Scoop (If you have it installed)"
    Write-Host "-----------------------------------------------"
    Write-Host "scoop install tesseract" -ForegroundColor Cyan
    Write-Host ""
    Write-Host ""
    Write-Host "After Installation:"
    Write-Host "------------------"
    Write-Host "1. Restart your terminal/IDE"
    Write-Host "2. Run this script again to verify"
    Write-Host "3. Test OCR with: python run_api_mode.py 'Contract #1.pdf'" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "============================================================================"
Write-Host ""

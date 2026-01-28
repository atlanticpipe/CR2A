#!/usr/bin/env pwsh
# Poppler Installation Script for Contract Analysis Tool
# Installs Poppler (PDF rendering library) required for OCR functionality

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Poppler Installation for Contract Analysis Tool" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Define installation paths
$tempPoppler = "$env:TEMP\poppler\poppler-24.08.0"
$installDir = "$env:LOCALAPPDATA\poppler"
$popplerBin = "$installDir\Library\bin"

# Check if Poppler is already in PATH
Write-Host "Checking if Poppler is already installed..." -ForegroundColor Yellow
$popplerInPath = $false
try {
    $null = Get-Command pdfinfo -ErrorAction Stop
    $popplerInPath = $true
    Write-Host "[OK] Poppler is already installed and in PATH!" -ForegroundColor Green
    & pdfinfo -v
    Write-Host ""
} catch {
    Write-Host "[X] Poppler not found in PATH" -ForegroundColor Red
}

# Check if source exists
if (-not (Test-Path $tempPoppler)) {
    Write-Host "Error: Poppler not found in TEMP directory" -ForegroundColor Red
    Write-Host "Expected location: $tempPoppler" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please download Poppler from:" -ForegroundColor Yellow
    Write-Host "https://github.com/oschwartz10612/poppler-windows/releases/" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

# Install Poppler to user directory
Write-Host "Installing Poppler to: $installDir" -ForegroundColor Yellow

try {
    # Remove old installation if exists
    if (Test-Path $installDir) {
        Write-Host "Removing old installation..." -ForegroundColor Yellow
        Remove-Item -Path $installDir -Recurse -Force
    }

    # Copy Poppler to user directory
    Write-Host "Copying Poppler files..." -ForegroundColor Yellow
    Copy-Item -Path $tempPoppler -Destination $installDir -Recurse -Force
    
    Write-Host "[OK] Poppler copied successfully!" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "Error installing Poppler: $_" -ForegroundColor Red
    exit 1
}

# Add to PATH
Write-Host "Adding Poppler to PATH..." -ForegroundColor Yellow

try {
    # Get current user PATH
    $currentPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    
    # Check if already in PATH
    if ($currentPath -like "*$popplerBin*") {
        Write-Host "[OK] Poppler already in PATH" -ForegroundColor Green
    } else {
        # Add to PATH
        $newPath = "$currentPath;$popplerBin"
        [System.Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Host "[OK] Added Poppler to PATH (permanent)" -ForegroundColor Green
    }
    
    # Add to current session PATH
    $env:Path += ";$popplerBin"
    Write-Host "[OK] Added Poppler to current session PATH" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "Error adding to PATH: $_" -ForegroundColor Red
    Write-Host "You may need to add manually: $popplerBin" -ForegroundColor Yellow
}

# Verify installation
Write-Host "Verifying Poppler installation..." -ForegroundColor Yellow
Write-Host ""

try {
    $pdfinfo = & "$popplerBin\pdfinfo.exe" -v 2>&1
    Write-Host "[OK] Poppler installed successfully!" -ForegroundColor Green
    Write-Host "Version: $pdfinfo" -ForegroundColor Cyan
    Write-Host ""
} catch {
    Write-Host "[X] Verification failed" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
}

# Summary
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Installation Summary" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installation Directory: $installDir" -ForegroundColor Yellow
Write-Host "Binaries Directory: $popplerBin" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Green
Write-Host "1. Restart your terminal or IDE to load new PATH" -ForegroundColor White
Write-Host "2. Test OCR with: python run_api_mode.py 'Contract #1.pdf'" -ForegroundColor White
Write-Host ""
Write-Host "If 'pdfinfo' command is not found after restart:" -ForegroundColor Yellow
Write-Host "  Add to PATH manually: $popplerBin" -ForegroundColor White
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan

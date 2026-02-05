# Install CR2A Certificate on User Machine
# This script installs the CR2A code signing certificate to trust the application

param(
    [string]$CertPath = ".\cert\CR2A_CodeSigning.cer"
)

Write-Host "CR2A Certificate Installation" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "For best results, run this script as Administrator" -ForegroundColor Yellow
    Write-Host ""
}

# Check if certificate file exists
if (-not (Test-Path $CertPath)) {
    Write-Host "ERROR: Certificate file not found at $CertPath" -ForegroundColor Red
    Write-Host "Please ensure the certificate file is in the correct location" -ForegroundColor Yellow
    exit 1
}

Write-Host "Installing certificate from: $CertPath" -ForegroundColor White
Write-Host ""

try {
    # Import to Trusted Root (requires admin) or Trusted Publishers (user level)
    if ($isAdmin) {
        Write-Host "Installing to Trusted Root Certification Authorities (machine-wide)..." -ForegroundColor Cyan
        Import-Certificate -FilePath $CertPath -CertStoreLocation Cert:\LocalMachine\Root
        Write-Host "Installing to Trusted Publishers (machine-wide)..." -ForegroundColor Cyan
        Import-Certificate -FilePath $CertPath -CertStoreLocation Cert:\LocalMachine\TrustedPublisher
    } else {
        Write-Host "Installing to Trusted Root Certification Authorities (current user)..." -ForegroundColor Cyan
        Import-Certificate -FilePath $CertPath -CertStoreLocation Cert:\CurrentUser\Root
        Write-Host "Installing to Trusted Publishers (current user)..." -ForegroundColor Cyan
        Import-Certificate -FilePath $CertPath -CertStoreLocation Cert:\CurrentUser\TrustedPublisher
    }
    
    Write-Host ""
    Write-Host "SUCCESS: Certificate installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "The CR2A application should now run without security warnings." -ForegroundColor Green
    Write-Host ""
    
    if (-not $isAdmin) {
        Write-Host "NOTE: For organization-wide deployment, run this script as Administrator" -ForegroundColor Yellow
        Write-Host "      to install the certificate for all users on this machine." -ForegroundColor Yellow
    }
    
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to install certificate" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Sign CR2A Application with Certificate
# This script signs the built executable with your code signing certificate

param(
    [string]$ExePath = ".\dist\CR2A\CR2A.exe",
    [string]$CertThumbprint = "",
    [string]$TimestampServer = "http://timestamp.digicert.com"
)

Write-Host "CR2A Application Signing Tool" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

# Check if executable exists
if (-not (Test-Path $ExePath)) {
    Write-Host "ERROR: Executable not found at $ExePath" -ForegroundColor Red
    Write-Host "Please build the application first with: python build_tools/build.py --target gui" -ForegroundColor Yellow
    exit 1
}

# Find certificate if thumbprint not provided
if ([string]::IsNullOrEmpty($CertThumbprint)) {
    Write-Host "Looking for code signing certificates..." -ForegroundColor Yellow
    $certs = Get-ChildItem -Path Cert:\CurrentUser\My -CodeSigningCert
    
    if ($certs.Count -eq 0) {
        Write-Host "ERROR: No code signing certificates found!" -ForegroundColor Red
        Write-Host "Please create a certificate first with: .\build_tools\create_self_signed_cert.ps1" -ForegroundColor Yellow
        exit 1
    }
    
    if ($certs.Count -eq 1) {
        $cert = $certs[0]
        Write-Host "Found certificate: $($cert.Subject)" -ForegroundColor Green
    } else {
        Write-Host "Multiple certificates found:" -ForegroundColor Yellow
        for ($i = 0; $i -lt $certs.Count; $i++) {
            Write-Host "  [$i] $($certs[$i].Subject) - Expires: $($certs[$i].NotAfter)" -ForegroundColor White
        }
        $selection = Read-Host "Select certificate number"
        $cert = $certs[[int]$selection]
    }
    
    $CertThumbprint = $cert.Thumbprint
}

Write-Host ""
Write-Host "Signing executable..." -ForegroundColor Cyan
Write-Host "  File: $ExePath" -ForegroundColor White
Write-Host "  Certificate: $CertThumbprint" -ForegroundColor White
Write-Host ""

# Sign the executable
try {
    Set-AuthenticodeSignature -FilePath $ExePath -Certificate (Get-Item "Cert:\CurrentUser\My\$CertThumbprint") -TimestampServer $TimestampServer
    
    Write-Host ""
    Write-Host "SUCCESS: Application signed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "NEXT STEPS:" -ForegroundColor Cyan
    Write-Host "1. Rebuild the installer: python build_tools/build.py --target installer"
    Write-Host "2. The installer will now include the signed executable"
    Write-Host "3. Distribute the certificate to other machines: .\build_tools\install_cert.ps1"
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to sign application" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

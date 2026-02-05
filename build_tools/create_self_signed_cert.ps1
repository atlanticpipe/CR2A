# Create Self-Signed Certificate for CR2A Application
# This script creates a code signing certificate for internal use

param(
    [string]$CertName = "CR2A Development",
    [string]$OutputPath = ".\cert"
)

Write-Host "Creating self-signed code signing certificate..." -ForegroundColor Cyan
Write-Host ""

# Create output directory if it doesn't exist
if (-not (Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath | Out-Null
}

# Generate certificate
$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject "CN=$CertName" `
    -KeyUsage DigitalSignature `
    -FriendlyName "$CertName Code Signing Certificate" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}") `
    -NotAfter (Get-Date).AddYears(5)

Write-Host "Certificate created successfully!" -ForegroundColor Green
Write-Host "Thumbprint: $($cert.Thumbprint)" -ForegroundColor Yellow
Write-Host ""

# Export certificate to file (for distribution to other machines)
$certPath = Join-Path $OutputPath "CR2A_CodeSigning.cer"
Export-Certificate -Cert $cert -FilePath $certPath | Out-Null

Write-Host "Certificate exported to: $certPath" -ForegroundColor Green
Write-Host ""

# Export with private key (password protected)
$password = Read-Host "Enter password for certificate export (for backup)" -AsSecureString
$pfxPath = Join-Path $OutputPath "CR2A_CodeSigning.pfx"
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $password | Out-Null

Write-Host "Certificate with private key exported to: $pfxPath" -ForegroundColor Green
Write-Host ""

Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "1. The certificate is now in your Personal certificate store"
Write-Host "2. To sign the application, run: .\build_tools\sign_application.ps1"
Write-Host "3. To install on other machines, distribute $certPath and run:"
Write-Host "   .\build_tools\install_cert.ps1"
Write-Host ""
Write-Host "Certificate Thumbprint (save this): $($cert.Thumbprint)" -ForegroundColor Yellow

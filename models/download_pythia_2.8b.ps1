# Download Pythia 2.8B Model for Bundled CR2A Distribution
# This script downloads the Pythia 2.8B Q4_K_M quantized model from HuggingFace
# File size: ~2.8 GB
# Estimated download time: 4-40 minutes depending on connection speed

$modelUrl = "https://huggingface.co/TheBloke/pythia-2.8b-GGUF/resolve/main/pythia-2.8b.Q4_K_M.gguf"
$outputFile = "pythia-2.8b-q4_k_m.gguf"
$expectedSizeMB = 2800

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Pythia 2.8B Model Downloader" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Source: HuggingFace (TheBloke/pythia-2.8b-GGUF)" -ForegroundColor Yellow
Write-Host "Size: ~2.8 GB" -ForegroundColor Yellow
Write-Host "Output: $outputFile" -ForegroundColor Yellow
Write-Host ""

# Check if file already exists
if (Test-Path $outputFile) {
    $existingSize = (Get-Item $outputFile).Length / 1MB
    Write-Host "WARNING: File already exists!" -ForegroundColor Red
    Write-Host "Existing file size: $([math]::Round($existingSize, 2)) MB" -ForegroundColor Red
    Write-Host ""
    $overwrite = Read-Host "Overwrite existing file? (y/n)"

    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "Download cancelled." -ForegroundColor Yellow
        exit 0
    }

    Write-Host "Removing existing file..." -ForegroundColor Yellow
    Remove-Item $outputFile -Force
}

Write-Host "Starting download..." -ForegroundColor Green
Write-Host "This may take 5-30 minutes depending on your connection speed." -ForegroundColor Yellow
Write-Host ""

try {
    # Download with progress bar
    $ProgressPreference = 'Continue'
    Invoke-WebRequest -Uri $modelUrl -OutFile $outputFile -UseBasicParsing

    Write-Host ""
    Write-Host "Download completed successfully!" -ForegroundColor Green

    # Verify file size
    $downloadedSize = (Get-Item $outputFile).Length / 1MB
    Write-Host "Downloaded file size: $([math]::Round($downloadedSize, 2)) MB" -ForegroundColor Cyan

    if ($downloadedSize -lt ($expectedSizeMB * 0.95)) {
        Write-Host "WARNING: File size is smaller than expected!" -ForegroundColor Red
        Write-Host "Expected: ~$expectedSizeMB MB" -ForegroundColor Red
        Write-Host "The download may have been incomplete. Please try again." -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Model ready for bundling!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Build the application:" -ForegroundColor White
    Write-Host "   python build_tools/build.py --target gui" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Build the installer:" -ForegroundColor White
    Write-Host "   python build_tools/build.py --target installer" -ForegroundColor Gray
    Write-Host ""
    Write-Host "The installer will include the Pythia model (~3-4 GB)." -ForegroundColor Yellow

} catch {
    Write-Host ""
    Write-Host "ERROR: Download failed!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Check your internet connection" -ForegroundColor White
    Write-Host "2. Verify you can access HuggingFace: https://huggingface.co" -ForegroundColor White
    Write-Host "3. Try downloading manually from:" -ForegroundColor White
    Write-Host "   $modelUrl" -ForegroundColor Gray
    Write-Host "4. Save as: $outputFile" -ForegroundColor White
    exit 1
}

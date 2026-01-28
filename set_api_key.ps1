# ============================================================================
# Set OpenAI API Key for Contract Analysis Tool (PowerShell)
# ============================================================================

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$ApiKey
)

Write-Host ""
Write-Host "============================================================================"
Write-Host "Contract Analysis Tool - API Key Setup"
Write-Host "============================================================================"
Write-Host ""

# Validate API key format
if (-not $ApiKey.StartsWith("sk-")) {
    Write-Host "ERROR: Invalid API key format" -ForegroundColor Red
    Write-Host ""
    Write-Host "API keys should start with 'sk-'"
    Write-Host ""
    Write-Host "Example valid key: sk-proj-abc123..."
    Write-Host ""
    exit 1
}

# Set for current session
$env:OPENAI_API_KEY = $ApiKey
Write-Host "✓ Set for current PowerShell session" -ForegroundColor Green

# Set permanently for user
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $ApiKey, "User")
Write-Host "✓ Set permanently for user account" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================================"
Write-Host "SUCCESS! API key has been set." -ForegroundColor Green
Write-Host "============================================================================"
Write-Host ""
Write-Host "The key is now available in THIS terminal session."
Write-Host "You can run the application immediately:"
Write-Host ""
Write-Host "  python main.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "For future terminal sessions, the key will be available automatically."
Write-Host ""
Write-Host "============================================================================"
Write-Host ""

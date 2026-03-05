<#
.SYNOPSIS
    Integration test script for CR2A Windows Installer.

.DESCRIPTION
    This PowerShell script performs automated verification of the CR2A installer.
    It validates two key properties:
    
    Property 1: File Bundling Completeness
    - For any file in the source application directory (dist/CR2A/), after running 
      the installer to a target directory, that file should exist in the installation 
      directory with identical content.
    - Validates: Requirements 1.1, 1.3, 1.4
    
    Property 2: Uninstall Completeness
    - For any file that was installed by the installer, after running the uninstaller, 
      that file should no longer exist in the installation directory.
    - Validates: Requirements 5.3

.PARAMETER InstallerPath
    Path to the installer executable. Default: "dist\CR2A_Setup.exe"

.PARAMETER InstallDir
    Target installation directory for testing. Default: "C:\TestInstall\CR2A"

.PARAMETER SourceDir
    Source directory containing the built application. Default: "dist\CR2A"

.PARAMETER SkipSourceComparison
    Skip file content comparison with source (faster but less thorough).

.PARAMETER Verbose
    Enable verbose output for debugging.

.EXAMPLE
    .\test_installer.ps1
    Run with default parameters.

.EXAMPLE
    .\test_installer.ps1 -InstallerPath "dist\CR2A_Setup.exe" -InstallDir "D:\TestInstall\CR2A"
    Run with custom installer path and installation directory.

.EXAMPLE
    .\test_installer.ps1 -SkipSourceComparison
    Run without file content comparison (faster).

.NOTES
    Author: CR2A Development Team
    Requires: Administrator privileges for installation to Program Files
    
    **Validates: Requirements 1.1, 1.3, 1.4, 5.3**
#>

[CmdletBinding()]
param(
    [Parameter(HelpMessage = "Path to the installer executable")]
    [string]$InstallerPath = "dist\CR2A_Setup.exe",
    
    [Parameter(HelpMessage = "Target installation directory for testing")]
    [string]$InstallDir = "C:\TestInstall\CR2A",
    
    [Parameter(HelpMessage = "Source directory containing the built application")]
    [string]$SourceDir = "dist\CR2A",
    
    [Parameter(HelpMessage = "Skip file content comparison with source")]
    [switch]$SkipSourceComparison
)

#--------------------------------
# Configuration
#--------------------------------

$ErrorActionPreference = "Stop"
$script:TestsPassed = 0
$script:TestsFailed = 0
$script:TestResults = @()

# Expected core files that must be present after installation
$ExpectedCoreFiles = @(
    "CR2A.exe",
    "uninstall.exe"
)

#--------------------------------
# Helper Functions
#--------------------------------

function Write-TestHeader {
    param([string]$Title)
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host ""
}

function Write-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Message = ""
    )
    
    $result = @{
        Name = $TestName
        Passed = $Passed
        Message = $Message
        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    }
    $script:TestResults += $result
    
    if ($Passed) {
        Write-Host "[PASS] " -ForegroundColor Green -NoNewline
        Write-Host $TestName
        $script:TestsPassed++
    } else {
        Write-Host "[FAIL] " -ForegroundColor Red -NoNewline
        Write-Host $TestName
        if ($Message) {
            Write-Host "       $Message" -ForegroundColor Yellow
        }
        $script:TestsFailed++
    }
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Gray
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-ErrorMessage {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Get-FileHashSafe {
    param([string]$FilePath)
    try {
        return (Get-FileHash -Path $FilePath -Algorithm SHA256).Hash
    } catch {
        return $null
    }
}

function Get-AllFilesRecursive {
    param([string]$Directory)
    
    if (-not (Test-Path $Directory)) {
        return @()
    }
    
    return Get-ChildItem -Path $Directory -Recurse -File | 
           ForEach-Object { $_.FullName.Substring($Directory.Length).TrimStart('\', '/') }
}

function Test-Prerequisites {
    Write-TestHeader "Prerequisites Check"
    
    $allPassed = $true
    
    # Check installer exists
    if (Test-Path $InstallerPath) {
        Write-TestResult "Installer exists at '$InstallerPath'" $true
    } else {
        Write-TestResult "Installer exists at '$InstallerPath'" $false "File not found"
        $allPassed = $false
    }
    
    # Check source directory exists (for comparison)
    if (-not $SkipSourceComparison) {
        if (Test-Path $SourceDir) {
            Write-TestResult "Source directory exists at '$SourceDir'" $true
        } else {
            Write-TestResult "Source directory exists at '$SourceDir'" $false "Directory not found - will skip source comparison"
            $script:SkipSourceComparison = $true
        }
    }
    
    # Check if installation directory is clean
    if (Test-Path $InstallDir) {
        Write-Warning "Installation directory already exists. Cleaning up..."
        try {
            Remove-Item -Path $InstallDir -Recurse -Force
            Write-TestResult "Cleaned up existing installation directory" $true
        } catch {
            Write-TestResult "Cleaned up existing installation directory" $false $_.Exception.Message
            $allPassed = $false
        }
    }
    
    return $allPassed
}

#--------------------------------
# Property 1: File Bundling Completeness
# Validates: Requirements 1.1, 1.3, 1.4
#--------------------------------

function Test-FileBundlingCompleteness {
    <#
    .SYNOPSIS
        Tests Property 1: File Bundling Completeness
    
    .DESCRIPTION
        For any file in the source application directory (dist/CR2A/), after running 
        the installer to a target directory, that file should exist in the installation 
        directory with identical content.
        
        **Validates: Requirements 1.1, 1.3, 1.4**
    #>
    
    Write-TestHeader "Property 1: File Bundling Completeness"
    Write-Info "Validates: Requirements 1.1, 1.3, 1.4"
    Write-Host ""
    
    $allPassed = $true
    
    # Step 1: Run silent installation
    Write-Info "Running silent installation to '$InstallDir'..."
    
    $installerFullPath = Resolve-Path $InstallerPath
    
    try {
        $process = Start-Process -FilePath $installerFullPath `
                                 -ArgumentList "/S", "/D=$InstallDir" `
                                 -Wait `
                                 -PassThru `
                                 -NoNewWindow
        
        if ($process.ExitCode -eq 0) {
            Write-TestResult "Silent installation completed" $true
        } else {
            Write-TestResult "Silent installation completed" $false "Exit code: $($process.ExitCode)"
            return $false
        }
    } catch {
        Write-TestResult "Silent installation completed" $false $_.Exception.Message
        return $false
    }
    
    # Wait a moment for file system to settle
    Start-Sleep -Seconds 2
    
    # Step 2: Verify installation directory was created
    if (Test-Path $InstallDir) {
        Write-TestResult "Installation directory created" $true
    } else {
        Write-TestResult "Installation directory created" $false "Directory not found: $InstallDir"
        return $false
    }
    
    # Step 3: Verify core expected files exist
    Write-Info "Verifying core files..."
    foreach ($file in $ExpectedCoreFiles) {
        $filePath = Join-Path $InstallDir $file
        if (Test-Path $filePath) {
            Write-TestResult "Core file exists: $file" $true
        } else {
            Write-TestResult "Core file exists: $file" $false "Missing file: $filePath"
            $allPassed = $false
        }
    }
    
    # Step 4: Compare with source directory (Property 1 - full verification)
    if (-not $SkipSourceComparison -and (Test-Path $SourceDir)) {
        Write-Host ""
        Write-Info "Comparing installed files with source directory..."
        
        $sourceFullPath = Resolve-Path $SourceDir
        $sourceFiles = Get-AllFilesRecursive -Directory $sourceFullPath
        $installedFiles = Get-AllFilesRecursive -Directory $InstallDir
        
        Write-Info "Source files count: $($sourceFiles.Count)"
        Write-Info "Installed files count: $($installedFiles.Count)"
        
        # Check that all source files are installed
        $missingFiles = @()
        $mismatchedFiles = @()
        
        foreach ($relativeFile in $sourceFiles) {
            $sourcePath = Join-Path $sourceFullPath $relativeFile
            $installedPath = Join-Path $InstallDir $relativeFile
            
            if (-not (Test-Path $installedPath)) {
                $missingFiles += $relativeFile
            } else {
                # Compare file content using hash
                $sourceHash = Get-FileHashSafe -FilePath $sourcePath
                $installedHash = Get-FileHashSafe -FilePath $installedPath
                
                if ($sourceHash -and $installedHash -and ($sourceHash -ne $installedHash)) {
                    $mismatchedFiles += $relativeFile
                }
            }
        }
        
        # Report results
        if ($missingFiles.Count -eq 0) {
            Write-TestResult "All source files installed ($($sourceFiles.Count) files)" $true
        } else {
            Write-TestResult "All source files installed" $false "Missing $($missingFiles.Count) files"
            foreach ($file in $missingFiles | Select-Object -First 10) {
                Write-Host "       - $file" -ForegroundColor Yellow
            }
            if ($missingFiles.Count -gt 10) {
                Write-Host "       ... and $($missingFiles.Count - 10) more" -ForegroundColor Yellow
            }
            $allPassed = $false
        }
        
        if ($mismatchedFiles.Count -eq 0) {
            Write-TestResult "All installed files match source content" $true
        } else {
            Write-TestResult "All installed files match source content" $false "Mismatched: $($mismatchedFiles.Count) files"
            foreach ($file in $mismatchedFiles | Select-Object -First 5) {
                Write-Host "       - $file" -ForegroundColor Yellow
            }
            $allPassed = $false
        }
    } else {
        Write-Info "Skipping source comparison (source directory not available or -SkipSourceComparison specified)"
    }
    
    # Step 5: Verify uninstaller was generated (Requirement 5.1)
    $uninstallerPath = Join-Path $InstallDir "uninstall.exe"
    if (Test-Path $uninstallerPath) {
        Write-TestResult "Uninstaller generated in installation directory" $true
    } else {
        Write-TestResult "Uninstaller generated in installation directory" $false
        $allPassed = $false
    }
    
    return $allPassed
}

#--------------------------------
# Property 2: Uninstall Completeness
# Validates: Requirements 5.3
#--------------------------------

function Test-UninstallCompleteness {
    <#
    .SYNOPSIS
        Tests Property 2: Uninstall Completeness
    
    .DESCRIPTION
        For any file that was installed by the installer, after running the uninstaller, 
        that file should no longer exist in the installation directory.
        
        **Validates: Requirements 5.3**
    #>
    
    Write-TestHeader "Property 2: Uninstall Completeness"
    Write-Info "Validates: Requirements 5.3"
    Write-Host ""
    
    $allPassed = $true
    
    # Step 1: Record installed files before uninstall
    Write-Info "Recording installed files before uninstall..."
    $installedFilesBefore = @()
    if (Test-Path $InstallDir) {
        $installedFilesBefore = Get-AllFilesRecursive -Directory $InstallDir
        Write-Info "Found $($installedFilesBefore.Count) installed files"
    } else {
        Write-TestResult "Installation directory exists before uninstall" $false
        return $false
    }
    
    # Step 2: Run silent uninstallation
    Write-Info "Running silent uninstallation..."
    
    $uninstallerPath = Join-Path $InstallDir "uninstall.exe"
    
    if (-not (Test-Path $uninstallerPath)) {
        Write-TestResult "Uninstaller exists" $false "File not found: $uninstallerPath"
        return $false
    }
    
    try {
        $process = Start-Process -FilePath $uninstallerPath `
                                 -ArgumentList "/S" `
                                 -Wait `
                                 -PassThru `
                                 -NoNewWindow
        
        if ($process.ExitCode -eq 0) {
            Write-TestResult "Silent uninstallation completed" $true
        } else {
            Write-TestResult "Silent uninstallation completed" $false "Exit code: $($process.ExitCode)"
            $allPassed = $false
        }
    } catch {
        Write-TestResult "Silent uninstallation completed" $false $_.Exception.Message
        return $false
    }
    
    # Wait for file system to settle
    Start-Sleep -Seconds 3
    
    # Step 3: Verify installation directory is removed
    if (-not (Test-Path $InstallDir)) {
        Write-TestResult "Installation directory removed" $true
    } else {
        # Check what files remain
        $remainingFiles = Get-AllFilesRecursive -Directory $InstallDir
        
        if ($remainingFiles.Count -eq 0) {
            # Directory exists but is empty - try to remove it
            try {
                Remove-Item -Path $InstallDir -Force
                Write-TestResult "Installation directory removed (was empty)" $true
            } catch {
                Write-TestResult "Installation directory removed" $false "Empty directory could not be removed"
                $allPassed = $false
            }
        } else {
            Write-TestResult "Installation directory removed" $false "Directory still exists with $($remainingFiles.Count) files"
            foreach ($file in $remainingFiles | Select-Object -First 10) {
                Write-Host "       - $file" -ForegroundColor Yellow
            }
            if ($remainingFiles.Count -gt 10) {
                Write-Host "       ... and $($remainingFiles.Count - 10) more" -ForegroundColor Yellow
            }
            $allPassed = $false
        }
    }
    
    # Step 4: Verify all previously installed files are removed
    $remainingInstalledFiles = @()
    foreach ($file in $installedFilesBefore) {
        $filePath = Join-Path $InstallDir $file
        if (Test-Path $filePath) {
            $remainingInstalledFiles += $file
        }
    }
    
    if ($remainingInstalledFiles.Count -eq 0) {
        Write-TestResult "All installed files removed ($($installedFilesBefore.Count) files)" $true
    } else {
        Write-TestResult "All installed files removed" $false "Remaining: $($remainingInstalledFiles.Count) files"
        $allPassed = $false
    }
    
    return $allPassed
}

#--------------------------------
# Summary Report
#--------------------------------

function Write-TestSummary {
    Write-TestHeader "Test Summary"
    
    $totalTests = $script:TestsPassed + $script:TestsFailed
    $passRate = if ($totalTests -gt 0) { [math]::Round(($script:TestsPassed / $totalTests) * 100, 1) } else { 0 }
    
    Write-Host "Total Tests:  $totalTests"
    Write-Host "Passed:       $($script:TestsPassed)" -ForegroundColor Green
    Write-Host "Failed:       $($script:TestsFailed)" -ForegroundColor $(if ($script:TestsFailed -gt 0) { "Red" } else { "Green" })
    Write-Host "Pass Rate:    $passRate%"
    Write-Host ""
    
    if ($script:TestsFailed -eq 0) {
        Write-Host "=" * 70 -ForegroundColor Green
        Write-Host " ALL TESTS PASSED" -ForegroundColor Green
        Write-Host "=" * 70 -ForegroundColor Green
        return 0
    } else {
        Write-Host "=" * 70 -ForegroundColor Red
        Write-Host " SOME TESTS FAILED" -ForegroundColor Red
        Write-Host "=" * 70 -ForegroundColor Red
        
        Write-Host ""
        Write-Host "Failed Tests:" -ForegroundColor Red
        foreach ($result in $script:TestResults | Where-Object { -not $_.Passed }) {
            Write-Host "  - $($result.Name)" -ForegroundColor Red
            if ($result.Message) {
                Write-Host "    $($result.Message)" -ForegroundColor Yellow
            }
        }
        return 1
    }
}

#--------------------------------
# Main Execution
#--------------------------------

function Main {
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Magenta
    Write-Host " CR2A Windows Installer Integration Tests" -ForegroundColor Magenta
    Write-Host "=" * 70 -ForegroundColor Magenta
    Write-Host ""
    Write-Host "Installer Path:    $InstallerPath"
    Write-Host "Install Directory: $InstallDir"
    Write-Host "Source Directory:  $SourceDir"
    Write-Host "Skip Comparison:   $SkipSourceComparison"
    Write-Host ""
    
    # Run prerequisites check
    $prereqPassed = Test-Prerequisites
    if (-not $prereqPassed) {
        Write-ErrorMessage "Prerequisites check failed. Cannot continue."
        return 1
    }
    
    # Run Property 1: File Bundling Completeness
    $property1Passed = Test-FileBundlingCompleteness
    
    # Run Property 2: Uninstall Completeness (only if installation succeeded)
    if ($property1Passed -or (Test-Path $InstallDir)) {
        $property2Passed = Test-UninstallCompleteness
    } else {
        Write-Warning "Skipping uninstall tests - installation did not complete successfully"
    }
    
    # Cleanup: Ensure test directory is removed
    if (Test-Path $InstallDir) {
        Write-Info "Cleaning up test installation directory..."
        try {
            Remove-Item -Path $InstallDir -Recurse -Force
        } catch {
            Write-Warning "Could not clean up test directory: $($_.Exception.Message)"
        }
    }
    
    # Print summary and return exit code
    return Write-TestSummary
}

# Run main function and exit with appropriate code
$exitCode = Main
exit $exitCode

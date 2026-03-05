# Poppler Binaries Setup for OCR Support

## Overview

CR2A requires Poppler binaries to convert PDF pages to images for OCR processing. These binaries must be present in `build_tools/poppler/` before building the application.

## Why Poppler is Needed

The `pdf2image` Python library requires Poppler's `pdftoppm` utility to convert PDF pages to images. When a user uploads an image-based (scanned) PDF, the OCR workflow:

1. Uses `pdf2image` to convert each PDF page to an image
2. `pdf2image` calls `pdftoppm.exe` from Poppler
3. Images are passed to Tesseract OCR for text extraction

## Download and Setup

### Option 1: Automated Download (Windows PowerShell)

```powershell
# Navigate to build_tools directory
cd build_tools

# Download Poppler for Windows
$popplerUrl = "https://github.com/oschwartz10612/poppler-windows/releases/download/v23.08.0-0/Release-23.08.0-0.zip"
Invoke-WebRequest -Uri $popplerUrl -OutFile "poppler.zip"

# Extract to temporary location
Expand-Archive -Path "poppler.zip" -DestinationPath "poppler_temp"

# Move binaries to correct location
New-Item -ItemType Directory -Force -Path "poppler/bin"
Copy-Item -Path "poppler_temp/poppler-23.08.0/Library/bin/*" -Destination "poppler/bin/" -Recurse

# Cleanup
Remove-Item "poppler.zip"
Remove-Item -Recurse "poppler_temp"

Write-Host "Poppler binaries installed successfully!" -ForegroundColor Green
```

### Option 2: Manual Download (All Platforms)

**Windows**:
1. Download Poppler for Windows from:
   - **Recommended**: https://github.com/oschwartz10612/poppler-windows/releases
   - Alternative: https://github.com/oschwartz10612/poppler-windows/releases/download/v23.08.0-0/Release-23.08.0-0.zip

2. Extract the ZIP file

3. Copy the contents of `poppler-XX.XX.X/Library/bin/` to `build_tools/poppler/bin/`

4. Verify the structure:
   ```
   build_tools/
   └── poppler/
       └── bin/
           ├── pdftoppm.exe
           ├── pdftocairo.exe
           ├── poppler.dll
           ├── cairo.dll
           ├── freetype.dll
           └── [other DLLs...]
   ```

**Linux** (using system Poppler):
```bash
# Install poppler-utils
sudo apt-get install poppler-utils  # Debian/Ubuntu
sudo dnf install poppler-utils      # Fedora/RHEL

# For bundled distribution, copy binaries
mkdir -p build_tools/poppler/bin
cp /usr/bin/pdftoppm build_tools/poppler/bin/
cp /usr/bin/pdftocairo build_tools/poppler/bin/
# Note: You may also need to copy shared libraries
```

**macOS** (using Homebrew):
```bash
# Install poppler
brew install poppler

# For bundled distribution, copy binaries
mkdir -p build_tools/poppler/bin
cp /opt/homebrew/bin/pdftoppm build_tools/poppler/bin/
cp /opt/homebrew/bin/pdftocairo build_tools/poppler/bin/
# Note: You may also need to copy dylib files
```

## Verification

After setup, verify the poppler binaries are present:

```bash
# Windows (PowerShell)
ls build_tools/poppler/bin/pdftoppm.exe

# Linux/Mac
ls build_tools/poppler/bin/pdftoppm
```

You should see the `pdftoppm` executable and supporting DLLs/libraries.

## Expected Directory Structure

After setup, your `build_tools/poppler/` should look like this:

```
build_tools/
├── poppler/
│   └── bin/
│       ├── pdftoppm.exe          # Main PDF to image converter
│       ├── pdftocairo.exe        # Alternative converter
│       ├── pdfinfo.exe           # PDF info utility
│       ├── poppler.dll           # Core Poppler library
│       ├── poppler-cpp.dll       # C++ interface
│       ├── cairo.dll             # Rendering library
│       ├── freetype.dll          # Font rendering
│       ├── jpeg8.dll             # JPEG support
│       ├── libpng16.dll          # PNG support
│       ├── libtiff.dll           # TIFF support
│       └── [30+ other DLLs]      # Dependencies
├── build.py
├── hook-PyQt5.py
├── hook-pytesseract.py
└── POPPLER_SETUP.md (this file)
```

Total size: ~23 MB

## Build Integration

Once poppler is set up, it will be automatically bundled when building:

```bash
# Build GUI application (includes poppler)
python build_tools/build.py --target gui

# Build full application with model (includes poppler)
python build_tools/build.py --target gui-full
```

The build script ([build.py](build.py)) includes poppler in the `data_files`:

```python
data_files=[
    ("assets", "assets"),
    ("config", "config"),
    ("build_tools/poppler", "poppler"),  # ← Bundled with application
]
```

## Troubleshooting

### "Poppler not found" error during build

**Symptom**: Build completes but OCR fails with "Unable to convert PDF to images"

**Solution**:
1. Verify `build_tools/poppler/bin/pdftoppm.exe` exists
2. Check that poppler binaries are included in the build output:
   ```bash
   ls dist/CR2A/_internal/poppler/bin/pdftoppm.exe
   ```
3. If missing, re-run the setup steps above and rebuild

### "Missing DLL" errors when running OCR

**Symptom**: Application starts but OCR fails with DLL errors

**Solution**:
1. Ensure you copied ALL files from `poppler-XX/Library/bin/`, not just the .exe files
2. Poppler has many DLL dependencies (30+ files) - all are needed
3. Check the OCR logs for which specific DLL is missing

### Poppler binaries too large for repository

**Symptom**: Don't want to commit 23 MB of binaries

**Solution**:
- The `.gitignore` is configured to exclude `build_tools/poppler/`
- Developers must download poppler locally using the setup script
- CI/CD pipelines should run the setup script before building
- Document the requirement in your README or build instructions

## CI/CD Integration

For automated builds, add the poppler setup to your build pipeline:

```yaml
# Example: GitHub Actions
steps:
  - name: Setup Poppler
    run: |
      cd build_tools
      ./setup_poppler.ps1  # Or equivalent for your platform

  - name: Build Application
    run: python build_tools/build.py --target gui-full
```

## Alternative: System Poppler (Development Only)

For development and testing (not distribution), you can use system-installed Poppler:

**Windows**:
```powershell
# Using Chocolatey
choco install poppler

# Verify installation
where pdftoppm
```

**Linux**:
```bash
sudo apt-get install poppler-utils
```

**Note**: System Poppler works for development, but for **distributed applications**, you must bundle the binaries so end users don't need to install Poppler separately.

## License

Poppler is released under the GNU General Public License (GPL). Ensure compliance when distributing:
- Include Poppler's GPL license in your distribution
- Provide attribution to the Poppler project
- Consider licensing implications for commercial use

See: https://poppler.freedesktop.org/

## Summary

- **Size**: ~23 MB
- **Required for**: OCR support (image-based PDF processing)
- **Location**: `build_tools/poppler/bin/`
- **Bundled**: Yes (automatically included in builds)
- **Version control**: Excluded from git (too large)
- **Setup**: Run setup script or manually download and extract

For questions or issues, see [docs/OCR_CONFIGURATION.md](../docs/OCR_CONFIGURATION.md).

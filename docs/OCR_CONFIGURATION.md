# OCR Configuration and Troubleshooting

## Overview

CR2A now includes full OCR (Optical Character Recognition) support for extracting text from image-based PDF files. This document explains how OCR works and what dependencies are required.

## Bundled OCR Components

The following OCR components are **automatically bundled** with the CR2A application:

### 1. Python Libraries
- **pytesseract** - Python wrapper for Tesseract OCR
- **PIL (Pillow)** - Image processing library
- **pdf2image** - Converts PDF pages to images

### 2. Poppler Binaries
- **Location**: `_internal/poppler/bin/` (in installed application)
- **Size**: ~23 MB
- **Purpose**: Converts PDF pages to images for OCR processing
- **Key files**: pdftoppm.exe, pdftocairo.exe, and supporting DLLs

## Required External Dependency: Tesseract OCR

**IMPORTANT**: The Tesseract OCR engine must be installed separately on the target machine.

### Download and Install Tesseract

**Windows (Recommended)**:
1. Download the official Windows installer from:
   https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (tesseract-ocr-w64-setup-v5.x.x.exe)
3. Install to the default location: `C:\Program Files\Tesseract-OCR`
4. No additional configuration needed - CR2A will auto-detect the installation

**Alternative Windows Locations**:
CR2A checks the following paths automatically:
- `C:\Program Files\Tesseract-OCR\tesseract.exe` (default)
- `C:\Program Files (x86)\Tesseract-OCR\tesseract.exe`
- `%USERPROFILE%\AppData\Local\Tesseract-OCR\tesseract.exe`

**Linux/Mac**:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS (Homebrew)
brew install tesseract

# Fedora/RHEL
sudo dnf install tesseract
```

## How OCR Works in CR2A

### Automatic Text Extraction Flow

1. **User uploads PDF** → Contract Uploader receives file
2. **Text extraction attempt** → PyPDF2 tries to extract text directly
3. **Check extraction result**:
   - If text found → Use extracted text (fast path)
   - If no text found → Document is image-based, proceed to OCR
4. **OCR Processing** (if enabled and dependencies available):
   - pdf2image converts PDF pages to images using **bundled Poppler**
   - pytesseract sends images to **Tesseract OCR** (must be installed)
   - Text is extracted from each page
   - Results are combined into full document text

### OCR Auto-Detection

CR2A automatically detects OCR capability at startup:

```python
# From analysis_engine.py
tesseract_path = self._find_tesseract()
if tesseract_path:
    logger.info(f"Found Tesseract at: {tesseract_path}")
    self.uploader = ContractUploader(tesseract_path=tesseract_path)
else:
    logger.warning("Tesseract not found, OCR may not work")
```

## Error Messages and Solutions

### "No text could be extracted from the PDF. Enable OCR support..."

**Cause**: OCR is disabled or Tesseract is not installed

**Solutions**:
1. Install Tesseract OCR (see installation instructions above)
2. Verify Tesseract is in PATH or in a standard location
3. Restart CR2A after installing Tesseract

### "OCR extraction failed: [pdf2image error]"

**Cause**: Poppler binaries not found or corrupted

**Solutions**:
1. Verify the application was built correctly with poppler included
2. Check that `poppler/bin/pdftoppm.exe` exists in the application directory
3. Rebuild the application if poppler is missing

### "DLL load failed while importing PIL/pdf2image"

**Cause**: Missing Visual C++ Runtime components

**Solutions**:
1. Install Visual C++ Redistributables:
   https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Restart your computer after installation

## Build Configuration

### For Developers: Building with OCR Support

The following components must be configured in `build_tools/build.py`:

```python
# Hidden imports (Python modules to bundle)
hidden_imports=[
    # ... other imports ...
    "pytesseract",
    "pdf2image",
    "PIL",
    "PIL.Image",
]

# Packages to collect (with all dependencies)
collect_packages=[
    # ... other packages ...
    "PIL",
    "pdf2image",
    "pytesseract",
]

# Data files (binaries and resources)
data_files=[
    # ... other data files ...
    ("build_tools/poppler", "poppler"),  # Poppler binaries
]
```

### Custom PyInstaller Hooks

**hook-pytesseract.py**:
```python
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('pytesseract')
datas = collect_data_files('pytesseract', include_py_files=True)
```

### Bundled Poppler Path Detection

In `contract_uploader.py`, the bundled poppler path is automatically detected:

```python
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    bundled_poppler = os.path.join(base_path, 'poppler', 'bin')
    if os.path.exists(bundled_poppler):
        poppler_path = bundled_poppler
```

## Testing OCR Functionality

### Test with a Sample PDF

1. Create or obtain an image-based PDF (scanned document)
2. Launch CR2A
3. Upload the PDF file
4. Check the console/log output for OCR messages:
   - "Starting OCR extraction for: [file]"
   - "Converted PDF to X images"
   - "Running OCR on page Y/X"
   - "Successfully extracted N characters using OCR"

### Expected Log Output (Success)

```
INFO: Found Tesseract at: C:\Program Files\Tesseract-OCR\tesseract.exe
INFO: Tesseract OCR enabled with custom path
INFO: Starting OCR extraction for: sample_contract.pdf
DEBUG: Converting PDF to images...
DEBUG: Using bundled poppler at: C:\...\dist\CR2A_Full\_internal\poppler\bin
INFO: Converted PDF to 5 images
DEBUG: Running OCR on page 1/5
DEBUG: Extracted 1234 characters from page 1
...
INFO: Successfully extracted 6789 characters using OCR
```

## Distribution Checklist

When distributing CR2A to end users:

- [x] pytesseract bundled in application
- [x] PIL (Pillow) bundled in application
- [x] pdf2image bundled in application
- [x] Poppler binaries bundled in application
- [ ] **User must install Tesseract OCR separately**
- [ ] Provide Tesseract installation instructions in user documentation
- [ ] Include link to Tesseract installer: https://github.com/UB-Mannheim/tesseract/wiki

## Future Enhancements

### Option 1: Bundle Tesseract with Installer

Pros:
- Zero configuration for end users
- Guaranteed OCR functionality

Cons:
- Adds ~50-60 MB to installer size
- License compliance considerations

### Option 2: Corporate Deployment Script

For enterprise deployments, create a post-install script:
```powershell
# install_tesseract.ps1
$tesseractUrl = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.0/tesseract-ocr-w64-setup-5.3.0.20221214.exe"
Invoke-WebRequest -Uri $tesseractUrl -OutFile "tesseract_installer.exe"
Start-Process -FilePath "tesseract_installer.exe" -ArgumentList "/S" -Wait
Remove-Item "tesseract_installer.exe"
```

## Summary

**What's Bundled**:
- Python libraries: pytesseract, PIL, pdf2image ✅
- Poppler binaries: pdftoppm.exe and dependencies ✅
- MSVCP runtime DLLs ✅

**What Users Must Install**:
- Tesseract OCR engine ⚠️ (one-time installation)

**Size Impact**:
- Base application: ~740 MB
- With OCR components: ~805 MB (+65 MB)
- With Pythia model: ~805 MB (model already included in Full build)
- With Tesseract (if bundled): ~860 MB (+55 MB) - Future enhancement

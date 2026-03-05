#!/bin/bash
# Download Pythia 2.8B Model for Bundled CR2A Distribution
# This script downloads the Pythia 2.8B Q4_K_M quantized model from HuggingFace
# File size: ~2.8 GB
# Estimated download time: 4-40 minutes depending on connection speed

MODEL_URL="https://huggingface.co/TheBloke/pythia-2.8b-GGUF/resolve/main/pythia-2.8b.Q4_K_M.gguf"
OUTPUT_FILE="pythia-2.8b-q4_k_m.gguf"
EXPECTED_SIZE_MB=2800

echo "========================================"
echo "Pythia 2.8B Model Downloader"
echo "========================================"
echo ""
echo "Source: HuggingFace (TheBloke/pythia-2.8b-GGUF)"
echo "Size: ~2.8 GB"
echo "Output: $OUTPUT_FILE"
echo ""

# Check if file already exists
if [ -f "$OUTPUT_FILE" ]; then
    EXISTING_SIZE=$(du -m "$OUTPUT_FILE" | cut -f1)
    echo "WARNING: File already exists!"
    echo "Existing file size: ${EXISTING_SIZE} MB"
    echo ""
    read -p "Overwrite existing file? (y/n): " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Download cancelled."
        exit 0
    fi

    echo "Removing existing file..."
    rm -f "$OUTPUT_FILE"
fi

echo "Starting download..."
echo "This may take 5-30 minutes depending on your connection speed."
echo ""

# Try wget first, fall back to curl
if command -v wget &> /dev/null; then
    echo "Using wget..."
    wget --progress=bar:force -O "$OUTPUT_FILE" "$MODEL_URL"
    DOWNLOAD_EXIT=$?
elif command -v curl &> /dev/null; then
    echo "Using curl..."
    curl -L --progress-bar -o "$OUTPUT_FILE" "$MODEL_URL"
    DOWNLOAD_EXIT=$?
else
    echo "ERROR: Neither wget nor curl found!"
    echo "Please install wget or curl to download the model."
    exit 1
fi

# Check if download succeeded
if [ $DOWNLOAD_EXIT -ne 0 ]; then
    echo ""
    echo "ERROR: Download failed!"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check your internet connection"
    echo "2. Verify you can access HuggingFace: https://huggingface.co"
    echo "3. Try downloading manually from:"
    echo "   $MODEL_URL"
    echo "4. Save as: $OUTPUT_FILE"
    exit 1
fi

# Verify file size
DOWNLOADED_SIZE=$(du -m "$OUTPUT_FILE" | cut -f1)
MINIMUM_SIZE=$((EXPECTED_SIZE_MB * 95 / 100))

echo ""
echo "Download completed!"
echo "Downloaded file size: ${DOWNLOADED_SIZE} MB"

if [ $DOWNLOADED_SIZE -lt $MINIMUM_SIZE ]; then
    echo "WARNING: File size is smaller than expected!"
    echo "Expected: ~${EXPECTED_SIZE_MB} MB"
    echo "The download may have been incomplete. Please try again."
    exit 1
fi

echo ""
echo "========================================"
echo "Model ready for bundling!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Build the application:"
echo "   python build_tools/build.py --target gui"
echo ""
echo "2. Build the installer:"
echo "   python build_tools/build.py --target installer"
echo ""
echo "The installer will include the Pythia model (~3-4 GB)."

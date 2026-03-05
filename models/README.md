# Pythia Model Files for Bundled Distribution

This directory contains Pythia language model files that are bundled directly into the CR2A installer for corporate distribution.

## Required Files

To enable bundled Pythia support, download the following model file and place it in this directory:

### Pythia 2.8B (Recommended)

**File**: `pythia-2.8b-q4_k_m.gguf`
**Size**: ~2.8 GB
**Source**: HuggingFace TheBloke repository
**Direct Download**: https://huggingface.co/TheBloke/pythia-2.8b-GGUF/resolve/main/pythia-2.8b.Q4_K_M.gguf

**Download Instructions**:

1. Click the direct download link above (or visit HuggingFace manually)
2. Save the file as: `pythia-2.8b-q4_k_m.gguf` (note the underscores)
3. Place it in this `models/` directory
4. Verify file size is approximately 2.8 GB

### Alternative: Pythia 1.4B (Lighter)

**File**: `pythia-1.4b-q4_k_m.gguf`
**Size**: ~1.4 GB
**Source**: HuggingFace TheBloke repository
**Direct Download**: https://huggingface.co/TheBloke/pythia-1.4b-GGUF/resolve/main/pythia-1.4b.Q4_K_M.gguf

**Download Instructions**:

1. Click the direct download link above
2. Save the file as: `pythia-1.4b-q4_k_m.gguf`
3. Place it in this `models/` directory
4. Verify file size is approximately 1.4 GB

## Using wget or curl (Linux/Mac/PowerShell)

### Pythia 2.8B:
```bash
# Using wget
wget -O pythia-2.8b-q4_k_m.gguf "https://huggingface.co/TheBloke/pythia-2.8b-GGUF/resolve/main/pythia-2.8b.Q4_K_M.gguf"

# Using curl
curl -L -o pythia-2.8b-q4_k_m.gguf "https://huggingface.co/TheBloke/pythia-2.8b-GGUF/resolve/main/pythia-2.8b.Q4_K_M.gguf"

# Using PowerShell (Windows)
Invoke-WebRequest -Uri "https://huggingface.co/TheBloke/pythia-2.8b-GGUF/resolve/main/pythia-2.8b.Q4_K_M.gguf" -OutFile "pythia-2.8b-q4_k_m.gguf"
```

### Pythia 1.4B:
```bash
# Using wget
wget -O pythia-1.4b-q4_k_m.gguf "https://huggingface.co/TheBloke/pythia-1.4b-GGUF/resolve/main/pythia-1.4b.Q4_K_M.gguf"

# Using curl
curl -L -o pythia-1.4b-q4_k_m.gguf "https://huggingface.co/TheBloke/pythia-1.4b-GGUF/resolve/main/pythia-1.4b.Q4_K_M.gguf"

# Using PowerShell (Windows)
Invoke-WebRequest -Uri "https://huggingface.co/TheBloke/pythia-1.4b-GGUF/resolve/main/pythia-1.4b.Q4_K_M.gguf" -OutFile "pythia-1.4b-q4_k_m.gguf"
```

## Verification

After downloading, verify the model is ready:

```bash
# Check that file exists and has correct size
ls -lh models/pythia-2.8b-q4_k_m.gguf

# Expected output (approximate):
# -rw-r--r-- 1 user user 2.8G pythia-2.8b-q4_k_m.gguf
```

## Building with Bundled Model

Once the model file is in place:

```bash
# Build application with bundled model
python build_tools/build.py --target gui

# Build installer with bundled model
python build_tools/build.py --target installer
```

The resulting installer will be ~3-4 GB and will include the Pythia model, allowing users to use Local AI immediately without any downloads.

## File Naming Convention

**IMPORTANT**: The model files MUST use underscores, not hyphens:
- Correct: `pythia-2.8b-q4_k_m.gguf` (underscores before 'k' and 'm')
- Incorrect: `pythia-2.8b.Q4_K_M.gguf` (original HuggingFace naming)

The model manager expects the underscore format for consistency.

## Directory Structure After Download

```
models/
├── README.md (this file)
├── README.txt (placeholder)
└── pythia-2.8b-q4_k_m.gguf (2.8GB - you download this)
```

## Troubleshooting

### "Model not found" error during build

Ensure:
1. Model file is in `models/` directory at project root
2. Filename matches exactly: `pythia-2.8b-q4_k_m.gguf`
3. File is not corrupted (check size matches expected ~2.8 GB)

### Download interrupted

If download is interrupted, you can resume with curl:
```bash
curl -C - -L -o pythia-2.8b-q4_k_m.gguf "https://huggingface.co/TheBloke/pythia-2.8b-GGUF/resolve/main/pythia-2.8b.Q4_K_M.gguf"
```

### Slow download

The model is 2.8 GB, so download time depends on your connection:
- 10 Mbps: ~40 minutes
- 50 Mbps: ~8 minutes
- 100 Mbps: ~4 minutes

## License

Pythia models are released under Apache 2.0 license by EleutherAI.
- Model: https://github.com/EleutherAI/pythia
- GGUF conversion by TheBloke: https://huggingface.co/TheBloke

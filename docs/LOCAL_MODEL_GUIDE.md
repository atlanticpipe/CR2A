# Local Model Guide - CR2A

Complete guide for using local AI models (Pythia) with CR2A for offline, private contract analysis.

## Table of Contents

- [Overview](#overview)
- [Hardware Requirements](#hardware-requirements)
- [Model Selection](#model-selection)
- [First-Time Setup](#first-time-setup)
- [Using Local AI](#using-local-ai)
- [Model Management](#model-management)
- [Fine-Tuning Guide](#fine-tuning-guide)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Overview

### What is Local AI?

CR2A supports embedded local AI models (Pythia) that run entirely on your CPU without requiring:
- Internet connection (after initial download)
- OpenAI API key or account
- Cloud services
- Data transmission outside your computer

### Benefits

- **Privacy**: 100% offline - contracts never leave your computer
- **Cost**: Free - no per-use API charges
- **Independence**: No dependency on external services
- **Availability**: Works anywhere, anytime (offline mode)

### Trade-offs

- **Speed**: 2-5 minutes per contract (vs 15-60 seconds with OpenAI)
- **RAM**: Requires 8GB+ RAM (16GB recommended)
- **Setup**: Initial 3GB model download
- **Accuracy**: Slightly lower than GPT-4o (can be improved with fine-tuning)

---

## Hardware Requirements

### Minimum Requirements

| Component | Specification |
|-----------|--------------|
| **OS** | Windows 10/11 (64-bit) |
| **CPU** | 4 cores @ 2.5GHz |
| **RAM** | 8 GB |
| **Storage** | 5 GB free space |
| **Internet** | One-time download only |

### Recommended Requirements

| Component | Specification | Why? |
|-----------|--------------|------|
| **CPU** | 8+ cores @ 3.0GHz | Faster inference |
| **RAM** | 16 GB | Smooth multitasking |
| **Storage** | 20 GB free space | Multiple models + cache |
| **SSD** | Solid State Drive | Faster model loading |

### Performance by CPU

| CPU Type | Analysis Time | User Experience |
|----------|---------------|-----------------|
| 4-core @ 2.5GHz | 4-5 minutes | Acceptable |
| 6-core @ 3.0GHz | 3-4 minutes | Good |
| 8-core @ 3.5GHz | 2-3 minutes | Excellent |
| 12+ core @ 4.0GHz | < 2 minutes | Outstanding |

---

## Model Selection

CR2A supports two Pythia model sizes. Choose based on your hardware and needs:

### Pythia 2.8B (Recommended)

**Best for**: Most users with 16GB+ RAM

| Aspect | Details |
|--------|---------|
| **Size** | 2.8 billion parameters |
| **Download** | ~3.0 GB |
| **RAM Usage** | 3.0 GB (loaded) |
| **Analysis Time** | 2-3 minutes per contract |
| **Accuracy** | High - suitable for most contracts |
| **Recommendation** | Default choice |

### Pythia 1.4B (Lighter)

**Best for**: Systems with 8-12GB RAM or older CPUs

| Aspect | Details |
|--------|---------|
| **Size** | 1.4 billion parameters |
| **Download** | ~1.5 GB |
| **RAM Usage** | 1.5 GB (loaded) |
| **Analysis Time** | 1.5-2 minutes per contract |
| **Accuracy** | Good - slightly less detailed |
| **Recommendation** | For resource-constrained systems |

### Comparison

| Factor | Pythia 2.8B | Pythia 1.4B |
|--------|-------------|-------------|
| Quality | Excellent | Very Good |
| Speed | Good | Very Good |
| RAM | 3GB | 1.5GB |
| Disk | 3GB | 1.5GB |

**Recommendation**: Start with Pythia 2.8B. Switch to 1.4B only if you experience memory issues.

---

## First-Time Setup

### Step 1: Enable Local AI

1. Launch CR2A
2. Open **File → Settings**
3. Under **AI Engine**, select **"Local AI (Pythia)"**
4. Choose your model: **Pythia 2.8B (Recommended)**
5. Click **OK**

### Step 2: First-Time Download

When you enable Local AI, CR2A will show a **First-Time Setup** dialog:

```
First-Time Setup

To use Local AI, CR2A needs to download the Pythia model.

Model: Pythia 2.8B (Quantized Q4_K_M)
Size: 2800MB (~2.8GB)
Download Time: ~5-15 minutes (depending on connection)

This is a one-time download. The model will be cached locally
and reused for all future analyses.

[Download Model]  [Use OpenAI Instead]  [Cancel]
```

3. Click **"Download Model"** to begin
4. Wait for download to complete (~5-15 minutes)
5. Model is now ready for use!

### Step 3: Verify Setup

1. Go to **Upload** tab
2. Select a small contract (< 5 pages)
3. Click **"Analyze Contract"**
4. Wait for analysis (~2-3 minutes)
5. Success! Local AI is working

---

## Using Local AI

### Analyzing Contracts

1. Select a contract file (PDF, DOCX, TXT)
2. Click **"Analyze Contract"**
3. Progress bar shows:
   - "Loading Pythia model..." (20-40 seconds, first time only)
   - "Analyzing contract..." (2-5 minutes)
4. Results appear in Analysis tab

**Note**: CR2A uses intelligent fuzzy logic matching to identify relevant clause categories even when exact terminology doesn't match. This helps Pythia find 30-50+ clause categories instead of just 7-10, improving analysis completeness.

### Chat/Q&A

Local AI also powers the Chat tab:
- Ask questions about analyzed contracts
- Responses take 15-30 seconds
- Conversational memory maintained

### Status Bar

The status bar shows which AI engine is active:
- **"Ready (Local AI: pythia-2.8b-q4)"** - Local AI enabled
- **"Ready (OpenAI API)"** - Cloud AI enabled

---

## Model Management

### Viewing Downloaded Models

1. **File → Settings**
2. **AI Engine → Manage Models...**
3. View all downloaded models with sizes

### Downloading Additional Models

1. Open **Model Manager**
2. Select model from **Available Models** list
3. Click **"Download Selected Model"**
4. Wait for download to complete

### Deleting Models

To free up disk space:

1. Open **Model Manager**
2. Select model from **Cached Models** list
3. Click **"Delete Selected Model"**
4. Confirm deletion

**Note**: You can re-download anytime.

### Model Storage Location

Models are stored in:
```
%APPDATA%\CR2A\models\
```

Example:
```
C:\Users\YourName\AppData\Roaming\CR2A\models\
  pythia-2.8b-q4_k_m.gguf  (~3GB)
  pythia-1.4b-q4_k_m.gguf  (~1.5GB)
```

---

## Fine-Tuning Guide

### Why Fine-Tune?

Fine-tuning a Pythia model on contract data can:
- Improve accuracy for your specific contract types
- Learn your organization's terminology
- Better detect domain-specific risks
- Customize clause categorization

### Prerequisites

- Python 3.11+
- HuggingFace account
- GPU with 16GB+ VRAM (for training)
- Contract dataset (100+ examples recommended)

### Quick Fine-Tuning Guide

#### 1. Prepare Training Data

Create a JSONL file with contract examples:

```jsonl
{"prompt": "Analyze this contract:\n[CONTRACT TEXT]", "completion": "[ANALYSIS JSON]"}
{"prompt": "Analyze this contract:\n[CONTRACT TEXT]", "completion": "[ANALYSIS JSON]"}
...
```

#### 2. Fine-Tune with HuggingFace

```bash
# Install training dependencies
pip install transformers datasets peft accelerate

# Fine-tune script (simplified)
python fine_tune_pythia.py \
  --model "EleutherAI/pythia-2.8b" \
  --data contracts_training.jsonl \
  --output custom-pythia-contracts
```

#### 3. Convert to GGUF Format

```bash
# Install llama.cpp tools
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make

# Convert to GGUF
python convert.py ../custom-pythia-contracts \
  --outtype q4_k_m \
  --outfile custom-pythia-contracts-q4.gguf
```

#### 4. Register in CR2A

1. Open **Model Manager**
2. Click **"Register Custom Model..."**
3. Enter display name: "Custom Pythia (Fine-tuned)"
4. Select your `.gguf` file
5. Click **OK**

Your fine-tuned model is now available in Settings!

### Advanced Fine-Tuning

For detailed fine-tuning instructions, see:
- [HuggingFace Fine-Tuning Guide](https://huggingface.co/docs/transformers/training)
- [Pythia Model Documentation](https://github.com/EleutherAI/pythia)
- [PEFT (Parameter-Efficient Fine-Tuning)](https://github.com/huggingface/peft)

---

## Performance Optimization

### Speed Up Analysis

#### 1. Close Background Applications

- Close web browsers, IDEs, heavy applications
- Free up RAM for the model
- Improves inference speed by 20-30%

#### 2. Adjust CPU Threads

1. **File → Settings**
2. **Local AI → CPU Threads**
3. Try different values:
   - **Auto-detect** (default)
   - **Half your CPU cores** (balanced)
   - **All CPU cores** (maximum speed)

#### 3. Use SSD Storage

- Store models on SSD instead of HDD
- Faster model loading (40s → 20s)

#### 4. Optimize Windows

```powershell
# Set high-performance power plan
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c

# Disable unnecessary startup programs
taskmgr → Startup → Disable unused apps
```

### Reduce Memory Usage

If experiencing memory issues:

1. **Switch to Pythia 1.4B** (uses 1.5GB vs 3GB)
2. **Close other applications** before analysis
3. **Restart CR2A** after analyzing many contracts
4. **Upgrade RAM** to 16GB+ if possible

---

## Troubleshooting

### Model Won't Load

**Error**: "Failed to load Pythia model"

**Causes & Solutions**:

1. **Insufficient RAM**
   - Close other applications
   - Try Pythia 1.4B instead of 2.8B
   - Upgrade to 16GB RAM

2. **Corrupted Model File**
   - Settings → Manage Models → Delete model
   - Re-download from Model Manager

3. **Incorrect Model Path**
   - Verify model exists: `%APPDATA%\CR2A\models\`
   - Re-download if missing

### Download Fails

**Error**: "Failed to download model"

**Causes & Solutions**:

1. **Network Issues**
   - Check internet connection
   - Disable VPN/proxy temporarily
   - Try again later (HuggingFace may be busy)

2. **Disk Space**
   - Free up 5GB disk space
   - Download to drive with more space

3. **Firewall/Antivirus**
   - Temporarily disable firewall
   - Add CR2A to antivirus exceptions

### Slow Analysis

**Symptom**: Analysis takes > 10 minutes

**Causes & Solutions**:

1. **CPU Bottleneck**
   - Close background applications
   - Increase CPU thread count in Settings
   - Consider faster CPU

2. **Large Contract**
   - Expected for 100+ page contracts
   - Use OpenAI API for faster results

3. **Swap/Paging**
   - Check Task Manager → Performance → Memory
   - If "Available" < 4GB, close applications
   - Upgrade RAM if consistently low

### Analysis Fails

**Error**: "Pythia inference failed"

**Causes & Solutions**:

1. **Out of Memory**
   - Close applications
   - Switch to Pythia 1.4B
   - Restart CR2A

2. **Invalid Contract**
   - Ensure file is valid PDF/DOCX
   - Try smaller contract first
   - Check error logs: `%APPDATA%\CR2A\logs\`

3. **Model Corruption**
   - Delete and re-download model
   - Verify model file size matches expected

### Poor Quality Results

**Symptom**: Missing clauses, incorrect analysis

**Causes & Solutions**:

1. **Model Limitations**
   - Pythia is less accurate than GPT-4o
   - Consider fine-tuning for your contracts
   - Use OpenAI for critical analyses

2. **Complex Contract**
   - Try OpenAI API for better accuracy
   - Break into smaller sections

3. **Hallucinations**
   - Enable "Exhaustive Analysis" (multi-pass verification)
   - This detects and removes hallucinations

---

## FAQ

### Q: Is Local AI as good as OpenAI?

**A**: Pythia provides good results but GPT-4o is more accurate. Local AI is best for:
- Privacy-sensitive contracts
- High-volume analysis (cost savings)
- Offline use
- After fine-tuning on your contract types

### Q: Can I use both OpenAI and Local AI?

**A**: Yes! Switch between them in Settings:
- Use Local AI for standard contracts (save money)
- Use OpenAI for critical contracts (higher accuracy)

### Q: How much does Local AI cost?

**A**: Free! Only costs are:
- One-time 3GB download (your internet bandwidth)
- Electricity (negligible, CPU-only)

### Q: Will Local AI get better over time?

**A**: Yes, in two ways:
1. **Updates**: We'll support newer/better models
2. **Fine-tuning**: Train on your contracts for better accuracy

### Q: Can I use Local AI on a laptop?

**A**: Yes, if your laptop has:
- 8GB+ RAM
- Modern CPU (i5/i7 8th gen+)
- Note: Laptop will use more battery during analysis

### Q: How do I switch back to OpenAI?

**A**: File → Settings → AI Engine → Select "OpenAI API (Cloud)" → Enter API key → OK

### Q: Can I distribute my fine-tuned model?

**A**: Check the license of your training data. Pythia itself is Apache 2.0 (permissive).

### Q: Does Local AI work offline?

**A**: Yes! After the first-time download, Local AI works completely offline.

### Q: Which model should I choose?

**A**:
- **Pythia 2.8B**: If you have 16GB+ RAM (recommended)
- **Pythia 1.4B**: If you have 8-12GB RAM or older CPU

### Q: How do I update models?

**A**: We'll notify you when new models are available. Delete old model → Download new version.

---

## Support

For additional help:

- **Documentation**: [README.md](../README.md)
- **User Manual**: [USER_MANUAL.md](../USER_MANUAL.md)
- **Error Logs**: `%APPDATA%\CR2A\logs\cr2a.log`
- **GitHub Issues**: Report bugs and feature requests

---

**Ready to analyze contracts privately with Local AI!**

*Last Updated: February 6, 2026*

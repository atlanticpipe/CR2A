# CR2A - Quick Start Guide

## Get Started in 5 Minutes! ⚡

This guide walks you through the complete CR2A workflow from contract upload to querying results. For detailed information, see the [User Manual](USER_MANUAL.md).

---

## Prerequisites (1 minute)

Before you start, make sure you have:

1. ✅ **Both executables**:
   - `ContractAnalysisCLI.exe` (Analyzer)
   - `CR2A.exe` (Chat Interface)

2. ✅ **OpenAI API Key** (required for analysis):
   ```bash
   # Set as environment variable
   set OPENAI_API_KEY=your-key-here
   
   # OR add to config.txt file
   openai_api_key=your-key-here
   ```

3. ✅ **A contract file** (PDF or DOCX format)
   - Or use a sample contract for testing

---

## Step 1: Analyze Your Contract (1 minute)

1. **Drag and drop** your contract file onto `ContractAnalysisCLI.exe`
   - Or run from command line: `ContractAnalysisCLI.exe your_contract.pdf`

2. **Wait** for the analysis to complete (30-60 seconds)
   - The analyzer extracts text from your document
   - Sends it to OpenAI for deep analysis
   - Validates and saves results as JSON

3. **Check the output**:
   - A JSON file is created: `your_contract_analysis.json`
   - The analyzer shows a summary of the contract

✅ **Success**: You see "✅ ANALYSIS COMPLETE!" and a JSON file is created

---

## Step 2: Chat Interface Opens Automatically (30 seconds)

After analysis completes:

1. **CR2A.exe launches automatically** with the results loaded
   - If it doesn't, manually run: `CR2A.exe --load your_contract_analysis.json`

2. **If Windows SmartScreen appears**:
   - Click "More info"
   - Click "Run anyway"

3. **Wait** for the window to open

✅ **Success**: You see the CR2A Chat Interface window with your contract loaded

---

## Step 3: Ask Your First Question (2 minutes)

1. **Type** a question in the input box:
   ```
   Who are the parties in this contract?
   ```

2. **Press Enter** or click "Send"

3. **Wait** for the response
   - **First time**: 30-60 seconds (downloading AI model)
   - **After that**: 3-10 seconds per question

4. **Read** the answer in the chat area

✅ **Success**: You got an answer!

---

## Alternative: Testing with Sample Data

If you don't have a contract file yet:

1. **Launch CR2A.exe manually**
2. **Click** "Load Contract" button
3. **Select** `examples/sample_contract.json` (included in the package)
4. **Start asking questions!**

This lets you test the chat interface without running the analyzer.

---

## Complete Workflow Summary

```
1. Upload Contract (PDF/DOCX)
   ↓
2. ContractAnalysisCLI.exe runs
   - Uses OpenAI API (requires internet)
   - Takes 30-60 seconds
   - Creates JSON file
   ↓
3. CR2A.exe opens automatically
   - Loads the JSON file
   - Ready for questions
   ↓
4. Ask questions using natural language
   - Uses local Pythia LLM (offline)
   - First query: 30-60 seconds (model download)
   - Subsequent queries: 3-10 seconds
```

---

## What to Ask

Try these example questions:

### About Parties
```
Who are the parties in this contract?
Who is the buyer?
What is the seller's address?
```

### About Money
```
What is the total contract value?
What are the payment terms?
Is there a deposit required?
```

### About Dates
```
When does the contract start?
When does the contract expire?
When is payment due?
```

### About Risks
```
What risks are identified?
What are the financial risks?
What is the highest severity risk?
```

### About Terms
```
What is the contract duration?
What are the delivery terms?
What is the warranty period?
```

---

## Tips for Better Results

### ✅ DO:
- Ask clear, specific questions
- Ask one thing at a time
- Use natural language
- Be patient (AI takes 3-10 seconds)

### ❌ DON'T:
- Ask multiple questions at once
- Expect instant answers
- Ask about things not in the contract
- Use overly complex language

---

## Common Issues

### "No OpenAI API Key" Error

**Solution**: Set your API key

```bash
set OPENAI_API_KEY=your-key-here
```

Or add to `config.txt` file.

### Analyzer Fails to Process Contract

**Solution**: Check your API key and internet connection

The analyzer requires OpenAI API access.

### "Windows protected your PC" Warning

**Solution**: Click "More info" → "Run anyway"

This is normal for unsigned executables.

### Chat Input is Grayed Out

**Solution**: Load a contract file first

Click "Load Contract" button.

### First Query Takes Forever

**Solution**: Be patient!

The AI model is downloading (~800MB). This only happens once.

### "File not found" Error

**Solution**: Check your file path

Make sure you're selecting a valid JSON file.

### Slow Responses

**Solution**: This is normal

CPU-based AI takes 3-10 seconds per query. This is expected.

---

## System Requirements

| Item | Requirement |
|------|-------------|
| **OS** | Windows 10/11 (64-bit) |
| **RAM** | 8GB minimum |
| **Disk** | 2GB free space |
| **Internet** | Required for contract analysis, first-time model download |
| **OpenAI API Key** | Required for contract analysis |

---

## File Locations

| Item | Location |
|------|----------|
| **Executables** | Where you extracted them |
| **Analysis Output** | Same folder as input contract |
| **AI Models** | `C:\Users\YourName\.cr2a\models\` |
| **Log Files** | `C:\Users\YourName\.cr2a\logs\` |
| **Config** | `config.txt` (in app folder) |

---

## Next Steps

### Learn More

- Read the [User Manual](USER_MANUAL.md) for detailed instructions
- Check the [FAQ](#frequently-asked-questions) for common questions
- Review [Troubleshooting](#troubleshooting) for issues

### Try Advanced Features

- Change AI model size (Settings)
- Enable OpenAI fallback (Settings)
- Load different contracts
- Ask complex questions

---

## Frequently Asked Questions

**Q: Do I need internet?**  
A: Only for first-time setup. After that, works offline.

**Q: Is my data sent to the cloud?**  
A: No! Everything runs on your computer.

**Q: Why is it slow?**  
A: AI runs on CPU (not GPU). 3-10 seconds is normal.

**Q: Can I use PDF files?**  
A: Yes! Drag and drop PDF/DOCX files onto ContractAnalysisCLI.exe first. The chat interface uses the resulting JSON files.

**Q: Do I need OpenAI API?**  
A: Yes, for contract analysis. The chat interface works offline after analysis.

**Q: Why two separate programs?**  
A: ContractAnalysisCLI.exe analyzes contracts (online, OpenAI). CR2A.exe queries results (offline, local AI).

**Q: What if I get an error?**  
A: Check log files in `C:\Users\YourName\.cr2a_chat\logs\`

---

## Getting Help

1. **Check the [User Manual](USER_MANUAL.md)** - Comprehensive guide
2. **Check log files** - Error details
3. **Contact support** - Include log files and error messages

---

## Quick Reference

### Essential Actions

```
Analyze Contract:  Drag PDF/DOCX onto ContractAnalysisCLI.exe
Launch Chat:       Double-click CR2A.exe (or auto-launches)
Load File:         Click "Load Contract" button (if needed)
Ask Question:      Type and press Enter
Close:             Click X or press Alt+F4
```

### Example Questions

```
Who are the parties?
What is the contract value?
When does it expire?
What are the risks?
What are the payment terms?
```

### Keyboard Shortcuts

```
Enter:    Send message
Ctrl+C:   Copy text
Ctrl+V:   Paste text
Alt+F4:   Close app
```

---

## That's It! 🎉

You're ready to use the complete CR2A system!

**Remember the workflow:**
1. Drag contract onto ContractAnalysisCLI.exe (uses OpenAI)
2. Wait for analysis to complete (30-60 seconds)
3. CR2A.exe opens automatically with results
4. Ask questions (uses local Pythia LLM, offline)
5. Get answers in 3-10 seconds!

**Or test with sample data:**
1. Launch CR2A.exe manually
2. Load examples/sample_contract.json
3. Start asking questions!

For more details, see the [User Manual](USER_MANUAL.md).

---

*CR2A v1.0.0 - Quick Start Guide*  
*Last Updated: January 30, 2026*

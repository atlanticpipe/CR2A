# CR2A User Manual

**Contract Review & Analysis - Desktop Application**

Version 1.0 | Last Updated: February 5, 2026

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Application Overview](#application-overview)
4. [Upload Tab](#upload-tab)
5. [Analysis Tab](#analysis-tab)
6. [Chat Tab](#chat-tab)
7. [History Tab](#history-tab)
8. [Version Tracking](#version-tracking)
9. [Settings](#settings)
10. [Tips & Best Practices](#tips--best-practices)
11. [Troubleshooting](#troubleshooting)
12. [FAQ](#faq)

---

## Introduction

### What is CR2A?

CR2A (Contract Review & Analysis) is a desktop application that uses artificial intelligence to analyze contracts and answer questions about them. It helps you:

- **Understand contracts quickly** - Extract key information automatically
- **Ask questions** - Get answers about contract terms, parties, risks, and obligations
- **Track changes** - Compare different versions of the same contract
- **Maintain history** - Keep all your analyses organized and accessible

### Key Features

✅ **AI-Powered Analysis** - Uses OpenAI GPT-4o to analyze contracts  
✅ **Natural Language Q&A** - Ask questions in plain English  
✅ **Version Tracking** - Automatically detect and compare contract versions  
✅ **Multiple Formats** - Supports PDF, DOCX, and TXT files  
✅ **Persistent History** - All analyses are saved automatically  
✅ **Export Options** - Export reports and chat logs  

---

## Getting Started

### System Requirements

**Minimum:**
- Windows 10/11 (64-bit)
- 4 GB RAM
- 1 GB free disk space
- Internet connection
- OpenAI API key

**Recommended:**
- 8 GB RAM
- 2 GB free disk space
- Broadband internet

### Installation

1. **Install Python 3.11+** (if not already installed)
2. **Extract CR2A** to a folder (e.g., `C:\Program Files\CR2A\`)
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Launch the application:**
   - Double-click `launch_gui.bat`, or
   - Run `python src/qt_gui.py`

### First Launch

When you first launch CR2A, you'll be prompted to enter your OpenAI API key.

#### Getting an OpenAI API Key

1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Sign in or create an account
3. Click **"Create new secret key"**
4. Copy the key (starts with `sk-`)
5. **Save it somewhere safe** - you can't view it again!

#### Entering Your API Key

1. Paste your API key in the settings dialog
2. Click **"Save"**
3. The key is encrypted and stored securely

You can change your API key later from **File → Settings**.

---

## Application Overview

CR2A has a clean, tabbed interface with four main sections:

```
┌─────────────────────────────────────────────┐
│  CR2A - Contract Review & Analysis          │
├─────────────────────────────────────────────┤
│  📄 Upload  │  📊 Analysis  │  💬 Chat  │  📜 History  │
├─────────────────────────────────────────────┤
│                                             │
│           [Tab Content Area]                │
│                                             │
└─────────────────────────────────────────────┘
```

### Navigation

- **Upload Tab** - Select and analyze contracts
- **Analysis Tab** - View structured analysis results
- **Chat Tab** - Ask questions about the contract
- **History Tab** - View past analyses and compare versions

### Menu Bar

**File Menu:**
- **Settings** - Configure OpenAI API key
- **Export** - Export analysis reports or chat logs
- **Exit** - Close the application

**Help Menu:**
- **About** - Application information

---

## Upload Tab

The Upload tab is where you select contracts for analysis.

### Selecting a Contract

1. Click **"Browse..."** button
2. Navigate to your contract file
3. Select a PDF, DOCX, or TXT file
4. Click **"Open"**

The selected file will be displayed with its name and size.

### Analysis Options

#### Standard Analysis (Default)

Standard analysis performs a single-pass analysis of your contract:
- Extracts parties, terms, dates, risks, obligations
- Identifies key clauses
- Provides compliance insights
- **Time:** 30-60 seconds for typical contracts

#### Exhaustive Analysis (Advanced)

Exhaustive analysis performs multiple passes with verification:
- ✅ All features of standard analysis
- ✅ Multi-pass verification to prevent hallucinations
- ✅ Confidence scores for each finding
- ✅ Conflict detection and resolution
- ✅ Coverage analysis

**To enable:**
1. Check **"Enable Exhaustive Analysis"**
2. Choose number of passes (2-5)
   - More passes = higher accuracy but longer time
   - 2 passes recommended for most contracts
3. Click **"Analyze Contract"**

**Time:** 2-5x longer than standard analysis

### Starting Analysis

1. Ensure a file is selected
2. Choose analysis mode (standard or exhaustive)
3. Click **"Analyze Contract"** button
4. Watch the progress bar
5. Wait for analysis to complete

**What happens during analysis:**
- Extracting text from document...
- Analyzing contract with AI...
- Parsing results...
- Saving to history...

### Duplicate Detection

If you upload a contract that CR2A has seen before, it will ask:

```
┌─────────────────────────────────────────┐
│  Duplicate Contract Detected            │
├─────────────────────────────────────────┤
│  This file appears similar to:          │
│  "Contract_v1.pdf" (Version 2)          │
│                                         │
│  Is this an updated version of the      │
│  same contract?                         │
│                                         │
│  [Yes]  [No]                            │
└─────────────────────────────────────────┘
```

- **Yes** - CR2A will track it as a new version and compare changes
- **No** - CR2A will treat it as a separate contract

---

## Analysis Tab

The Analysis tab displays structured results from the contract analysis.

### Contract Overview

At the top, you'll see:
- **Filename** - Name of the analyzed contract
- **Analysis Date** - When it was analyzed
- **File Size** - Size of the document
- **Page Count** - Number of pages

### Sections

Results are organized into expandable sections:

#### � Clauses

All identified clauses grouped by category:
- Payment Terms
- Liability
- Termination
- Warranties
- Confidentiality
- Intellectual Property
- And more...

Each clause shows:
- **Text** - The actual clause content
- **Page** - Where it appears in the document
- **Risk Level** - Low, Medium, or High

#### ⚠️ Risks

Identified risks with:
- **Description** - What the risk is
- **Severity** - Low, Medium, High, or Critical
- **Related Clause** - Which clause contains the risk
- **Mitigation** - Suggested actions

#### 📜 Compliance Issues

Potential compliance concerns:
- **Regulation** - Which regulation (GDPR, CCPA, etc.)
- **Issue** - Description of the concern
- **Severity** - Impact level

#### 📝 Obligations

Key obligations extracted from the contract:
- Party responsible
- Obligation description
- Deadline (if specified)

#### 💰 Financial Terms

Money-related information:
- Contract value
- Payment schedule
- Penalties
- Deposits

#### 📅 Important Dates

Key dates from the contract:
- Start date
- End date
- Renewal dates
- Milestone dates

### Exhaustive Analysis Results

If you used exhaustive analysis, you'll also see:

#### Confidence Scores

Each finding includes a confidence score:
- **High (>80%)** - Very confident
- **Medium (60-80%)** - Reasonably confident
- **Low (<60%)** - Less certain

#### Verification Status

- ✅ **Verified** - Confirmed across multiple passes
- ⚠️ **Uncertain** - Conflicting information found
- ❌ **Not Found** - Could not be verified

### Exporting Results

**File → Export → Export Analysis Report**
- Saves a text file with all analysis results
- Includes all sections and findings
- Easy to share or archive

---

## Chat Tab

The Chat tab lets you ask questions about the analyzed contract.

### Asking Questions

1. Type your question in the input box at the bottom
2. Press **Enter** or click **"Send"**
3. Wait 2-5 seconds for the response
4. Read the answer in the chat history

### Example Questions

#### About Parties
```
Who are the parties in this contract?
Who is the buyer?
What is the seller's address?
```

#### About Money
```
What is the total contract value?
What are the payment terms?
When is payment due?
Are there any penalties?
```

#### About Dates
```
When does the contract start?
When does it expire?
What is the contract duration?
```

#### About Terms
```
What are the termination conditions?
What is the warranty period?
What are the delivery terms?
```

#### About Risks
```
What risks are identified?
What are the high-severity risks?
How can we mitigate the risks?
```

#### About Clauses
```
What does the liability clause say?
Where is the payment clause?
What page is the termination clause on?
```

### Tips for Better Answers

✅ **DO:**
- Ask clear, specific questions
- Ask one thing at a time
- Use natural language
- Be patient (AI takes 2-5 seconds)

❌ **DON'T:**
- Ask multiple questions at once
- Expect instant answers
- Ask about things not in the contract
- Use overly complex language

### Chat History

All questions and answers are saved in the chat history:
- Scroll up to review previous Q&A
- Copy text by selecting and pressing Ctrl+C
- Export the entire conversation

### Exporting Chat

**File → Export → Export Chat Log**
- Saves all questions and answers to a text file
- Includes timestamps
- Easy to share with colleagues

---

## History Tab

The History tab shows all previously analyzed contracts.

### Contract List

Each entry shows:
- **Filename** - Name of the contract
- **Analysis Date** - When it was analyzed
- **Version** - Current version number (if tracked)
- **Versioned Clauses** - Number of clauses with multiple versions

### Loading a Historical Analysis

1. Click on a contract in the list
2. Click **"Load Analysis"** button
3. The analysis appears in the Analysis tab
4. You can now ask questions about it in the Chat tab

### Deleting Analyses

1. Select a contract in the list
2. Click **"Delete"** button
3. Confirm the deletion

**Note:** This only deletes the analysis record, not the original contract file.

### Version Information

For contracts with multiple versions, you'll see:
- **Current Version** - Latest version number
- **Version Count** - Total number of versions
- **Last Updated** - When the latest version was analyzed

---

## Version Tracking

CR2A automatically tracks contract versions and helps you compare changes.

### How Version Tracking Works

1. **First Upload** - Creates Version 1
2. **Subsequent Uploads** - CR2A checks if it's a duplicate:
   - **Exact match** (same file hash) → Asks if it's an update
   - **Similar filename** → Asks if it's an update
3. **Confirm Update** - You confirm it's a new version
4. **Automatic Comparison** - CR2A compares and tracks changes
5. **View Changes** - Use History tab to see differences

### Comparing Versions

1. Go to **History Tab**
2. Select a contract with multiple versions
3. Click **"Compare Versions"** button
4. Choose two versions to compare
5. Click **"Compare"**

### Version Comparison View

The comparison view shows:

#### Change Summary
- **Modified Clauses** - Count of changed clauses
- **Added Clauses** - Count of new clauses
- **Deleted Clauses** - Count of removed clauses
- **Unchanged Clauses** - Count of clauses that didn't change

#### Side-by-Side Diff

Clauses are displayed side-by-side with color coding:

- 🟢 **Green** - Added text
- 🔴 **Red** - Deleted text
- 🟡 **Yellow** - Modified text
- ⚪ **White** - Unchanged text

#### Clause Details

For each changed clause:
- **Clause Type** - Category (e.g., Payment Terms)
- **Version Numbers** - Which versions it appears in
- **Change Type** - Modified, Added, or Deleted
- **Text Diff** - Exact changes highlighted

### Version Tracking Benefits

✅ **Audit Trail** - See exactly what changed between versions  
✅ **Risk Management** - Identify new risks in updated contracts  
✅ **Compliance** - Track changes to compliance-related clauses  
✅ **Negotiation** - Compare original vs. negotiated terms  

---

## Settings

Access settings from **File → Settings**.

### OpenAI API Key

- **View Current Key** - Shows masked key (sk-***...)
- **Update Key** - Enter a new API key
- **Validate** - Test if the key works

**To update your API key:**
1. Open **File → Settings**
2. Enter your new API key
3. Click **"Save"**
4. The application will reinitialize with the new key

### Configuration Files

CR2A stores configuration in:
- **Config:** `%APPDATA%\CR2A\config.json`
- **Logs:** `%APPDATA%\CR2A\logs\cr2a.log`
- **Database:** `%APPDATA%\CR2A\versions.db`
- **History:** `%APPDATA%\CR2A\history\`

---

## Tips & Best Practices

### For Best Analysis Results

1. **Use clear, readable contracts**
   - Avoid heavily scanned or low-quality PDFs
   - Ensure text is selectable (not just images)

2. **Check file size**
   - Contracts under 50 pages work best
   - Very large contracts may take longer

3. **Use exhaustive analysis for critical contracts**
   - Important agreements
   - High-value contracts
   - Contracts with complex terms

4. **Review the analysis**
   - AI is powerful but not perfect
   - Always review critical findings
   - Use Q&A to clarify unclear points

### For Better Q&A

1. **Be specific**
   - Instead of "What about payment?" ask "What is the payment schedule?"

2. **Ask follow-up questions**
   - Build on previous answers
   - Drill down into details

3. **Reference specific sections**
   - "What does section 5.2 say about..."
   - "Explain the liability clause"

### For Version Tracking

1. **Use consistent naming**
   - `Contract_v1.pdf`, `Contract_v2.pdf`
   - Helps CR2A detect versions

2. **Confirm version updates**
   - When prompted, confirm if it's truly an update
   - This ensures accurate version tracking

3. **Compare before signing**
   - Always compare the final version with previous drafts
   - Check for unexpected changes

---

## Troubleshooting

### Application Won't Start

**Problem:** Double-clicking launch_gui.bat does nothing

**Solutions:**
1. Check Python is installed: `python --version`
2. Install dependencies: `pip install -r requirements.txt`
3. Try running directly: `python src/qt_gui.py`
4. Check logs in `%APPDATA%\CR2A\logs\cr2a.log`

### API Key Errors

**Problem:** "Invalid API key" or "Authentication failed"

**Solutions:**
1. Verify your API key is correct
2. Check it starts with `sk-`
3. Ensure you have API credits
4. Try generating a new key from OpenAI
5. Update key in **File → Settings**

### Analysis Fails

**Problem:** Analysis starts but fails with an error

**Solutions:**
1. **Check internet connection** - OpenAI API requires internet
2. **Check file format** - Ensure PDF/DOCX is not corrupted
3. **Check file size** - Very large files may timeout
4. **Check API credits** - Ensure you have sufficient credits
5. **Try again** - Temporary API issues may resolve

### No Text Extracted

**Problem:** "No text could be extracted from the contract"

**Solutions:**
1. **Check if PDF is image-based** - Scanned PDFs need OCR
2. **Install Tesseract OCR** - For scanned document support
3. **Try a different format** - Convert to DOCX if possible
4. **Check if password-protected** - Remove password first

### Chat Not Working

**Problem:** Questions don't get answers

**Solutions:**
1. **Ensure contract is analyzed** - Must analyze before asking questions
2. **Check internet connection** - Q&A requires OpenAI API
3. **Wait for response** - Can take 2-5 seconds
4. **Check API credits** - Ensure sufficient credits
5. **Restart application** - May resolve temporary issues

### Version Comparison Not Working

**Problem:** Can't compare versions or comparison shows no changes

**Solutions:**
1. **Ensure multiple versions exist** - Need at least 2 versions
2. **Check version confirmation** - Must confirm updates when prompted
3. **Restart application** - Reinitialize versioning system
4. **Check database** - Ensure `%APPDATA%\CR2A\versions.db` exists

### Slow Performance

**Problem:** Application is slow or unresponsive

**Solutions:**
1. **Close other applications** - Free up RAM
2. **Use standard analysis** - Exhaustive mode is slower
3. **Analyze smaller contracts** - Break large contracts into sections
4. **Check internet speed** - Slow connection affects API calls
5. **Restart application** - Clear memory

---

## FAQ

### General Questions

**Q: Do I need internet to use CR2A?**  
A: Yes, CR2A requires internet for OpenAI API calls during analysis and Q&A.

**Q: Is my data sent to OpenAI?**  
A: Yes, contract text is sent to OpenAI for analysis. Review OpenAI's privacy policy for details.

**Q: Can I use CR2A offline?**  
A: No, the application requires internet for AI features. You can view previously analyzed contracts offline.

**Q: How much does it cost?**  
A: CR2A is free, but you need an OpenAI API key which has usage costs. Check OpenAI pricing for current rates.

### Analysis Questions

**Q: How accurate is the analysis?**  
A: CR2A uses GPT-4o which is highly accurate, but always review critical findings. Use exhaustive analysis for higher confidence.

**Q: What file formats are supported?**  
A: PDF, DOCX, and TXT files.

**Q: Can it analyze scanned PDFs?**  
A: Yes, with Tesseract OCR installed. Otherwise, only text-based PDFs work.

**Q: How long does analysis take?**  
A: 30-60 seconds for typical contracts, longer for large or complex documents.

**Q: Can I analyze contracts in other languages?**  
A: Yes, OpenAI supports multiple languages, but results may vary.

### Version Tracking Questions

**Q: How does CR2A detect duplicates?**  
A: By file hash (exact matches) and filename similarity (fuzzy matching).

**Q: Can I manually mark contracts as versions?**  
A: Not currently. CR2A relies on automatic detection and your confirmation.

**Q: How many versions can I track?**  
A: Unlimited. All versions are stored in the database.

**Q: Can I compare non-sequential versions?**  
A: Yes, you can compare any two versions (e.g., v1 vs v5).

### Technical Questions

**Q: Where is my data stored?**  
A: Locally in `%APPDATA%\CR2A\`. Nothing is stored in the cloud except during API calls.

**Q: Can I export my data?**  
A: Yes, export analysis reports and chat logs from the File menu.

**Q: Can I use a different AI model?**  
A: Currently only OpenAI GPT-4o is supported.

**Q: Is my API key secure?**  
A: Yes, it's encrypted and stored locally in `config.json`.

---

## Getting Help

### Support Resources

1. **Documentation**
   - This user manual
   - [Versioning Guide](docs/VERSIONING_USER_GUIDE.md)
   - [README.md](README.md)

2. **Logs**
   - Check `%APPDATA%\CR2A\logs\cr2a.log` for errors
   - Include log excerpts when reporting issues

3. **GitHub Issues**
   - Report bugs and request features
   - Search existing issues first

### Reporting Issues

When reporting an issue, include:
- CR2A version
- Windows version
- Error message (exact text)
- Steps to reproduce
- Relevant log excerpts
- Screenshot (if applicable)

---

## Appendix

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open file (Upload tab) |
| `Ctrl+S` | Save/Export |
| `Ctrl+Q` | Quit application |
| `Enter` | Send question (Chat tab) |
| `Ctrl+C` | Copy selected text |
| `Ctrl+V` | Paste text |

### File Locations

| Item | Location |
|------|----------|
| Configuration | `%APPDATA%\CR2A\config.json` |
| Logs | `%APPDATA%\CR2A\logs\cr2a.log` |
| Version Database | `%APPDATA%\CR2A\versions.db` |
| History Files | `%APPDATA%\CR2A\history\` |

### Supported File Types

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Text-based or scanned (with OCR) |
| Word | `.docx` | Modern Word format |
| Text | `.txt` | Plain text files |

---

**Thank you for using CR2A!**

For the latest updates and documentation, visit the project repository.

*CR2A User Manual v1.0 - February 5, 2026*

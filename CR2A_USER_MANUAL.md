# CR2A Unified Application - User Manual

## Welcome to CR2A! 🎉

CR2A (Clause Risk, Compliance & Redlining Analysis) is a powerful desktop application that helps you analyze contracts and ask questions about them using AI. Upload a contract, get instant analysis, and chat with an AI about your contract - all in one application!

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Installation and Setup](#installation-and-setup)
3. [First Time Configuration](#first-time-configuration)
4. [Uploading and Analyzing Contracts](#uploading-and-analyzing-contracts)
5. [Understanding Analysis Results](#understanding-analysis-results)
6. [Querying Your Contract](#querying-your-contract)
7. [Settings and Configuration](#settings-and-configuration)
8. [Tips and Best Practices](#tips-and-best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Frequently Asked Questions](#frequently-asked-questions)

---

## Getting Started

### What is CR2A?

CR2A is an all-in-one contract analysis tool that:

- **Analyzes** PDF and DOCX contract documents
- **Extracts** key clauses, risks, and compliance issues
- **Identifies** redlining suggestions
- **Answers** your questions about the contract using AI

### What You Need

**System Requirements:**
- Windows 10 or Windows 11 (64-bit)
- Minimum 8GB RAM (16GB recommended)
- 2GB free disk space
- Internet connection (for contract analysis only)

**Required:**
- OpenAI API key (for contract analysis)
- Contract documents in PDF or DOCX format

**Optional:**
- Pythia AI model (downloads automatically for offline querying)

### Key Features

✅ **Upload Screen** - Select and validate contract files  
✅ **Analysis Engine** - AI-powered contract analysis using OpenAI  
✅ **Progress Tracking** - Real-time analysis progress updates  
✅ **Chat Interface** - Ask questions about your analyzed contracts  
✅ **Offline Querying** - Local AI processes queries without internet  
✅ **Secure Storage** - Encrypted API key storage  

---

## Installation and Setup

### Step 1: Download and Extract

1. Download the CR2A application package
2. Extract the ZIP file to a location like:
   - `C:\Program Files\CR2A\`
   - `C:\Users\YourName\Applications\CR2A\`
3. Locate `CR2A.exe` in the extracted folder

### Step 2: First Launch

1. **Double-click** `CR2A.exe` to launch the application
2. If Windows SmartScreen appears:
   - Click **"More info"**
   - Click **"Run anyway"**
3. The application window will open

### Step 3: Configuration Directory

On first launch, CR2A automatically creates:

**Configuration Directory:**
```
%APPDATA%\CR2A\
├── config.json          (encrypted API key and settings)
└── logs\
    └── cr2a.log        (application logs)
```

**Location:** `C:\Users\YourName\AppData\Roaming\CR2A\`

---

## First Time Configuration

### OpenAI API Key Setup

CR2A requires an OpenAI API key to analyze contracts. On first launch, you'll see a settings dialog.

#### Getting an OpenAI API Key

1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Sign in or create an OpenAI account
3. Click **"Create new secret key"**
4. Copy the key (starts with `sk-`)
5. **Important:** Save the key somewhere safe - you can't view it again!

#### Entering Your API Key

1. When the settings dialog appears, paste your API key
2. The key format should be: `sk-...` (starts with "sk-")
3. Click **"Save"**
4. The key is encrypted and stored securely

#### Updating Your API Key Later

1. Click the **Settings** menu in the application
2. Select **"API Key Configuration"**
3. Enter your new API key
4. Click **"Save"**

---

## Uploading and Analyzing Contracts

### Step 1: Upload Screen

When you launch CR2A, you'll see the **Upload Screen**:

- **Title:** "CR2A Contract Analysis"
- **Select File Button:** Choose your contract document
- **File Information:** Shows selected file details
- **Analyze Button:** Starts the analysis (disabled until file selected)

### Step 2: Selecting a Contract File

1. Click the **"Select Contract File"** button
2. A file browser window opens
3. Navigate to your contract document
4. Select a **PDF** or **DOCX** file
5. Click **"Open"**

**Supported Formats:**
- ✅ PDF files (`.pdf`)
- ✅ Word documents (`.docx`)
- ❌ Other formats are not supported

### Step 3: File Validation

After selecting a file, CR2A displays:

- **Filename:** The name of your contract
- **File Size:** Size in MB or KB
- **Status:** "Ready to analyze" or error message

**Common Errors:**
- "Unsupported file format" - Use PDF or DOCX only
- "File not readable" - Check file permissions
- "File too large" - Files over 100MB may not be supported

### Step 4: Starting Analysis

1. Verify the correct file is selected
2. Click the **"Analyze Contract"** button
3. The application transitions to the **Analysis Screen**

### Step 5: Analysis Progress

During analysis, you'll see:

- **Progress Bar:** Visual indication of progress
- **Status Messages:** Current analysis phase
  - "Extracting text from document..."
  - "Analyzing contract clauses..."
  - "Identifying risks and compliance issues..."
  - "Generating redlining suggestions..."
- **Estimated Time:** Appears if analysis takes > 10 seconds

**Typical Analysis Times:**
- 1-page contract: ~5 seconds
- 10-page contract: ~15 seconds
- 25-page contract: ~35 seconds
- 50-page contract: ~60 seconds

### Step 6: Analysis Completion

When analysis completes:

1. You'll see a **"Analysis Complete"** message
2. The application automatically transitions to the **Chat Screen**
3. Your contract is now ready for querying!

### Handling Analysis Errors

If analysis fails, you'll see an error message with:

- **Error Type:** Network error, API error, etc.
- **Error Details:** Specific information about the failure
- **Retry Button:** Try the analysis again
- **Cancel Button:** Return to upload screen

**Common Errors:**
- "Invalid API key" - Check your API key in settings
- "Network connection failed" - Check your internet connection
- "Rate limit exceeded" - Wait a few minutes and retry
- "API timeout" - Try again or check OpenAI status

---

## Understanding Analysis Results

### What Gets Analyzed?

CR2A extracts and analyzes:

1. **Contract Metadata**
   - Filename
   - Analysis date and time
   - Page count
   - File size

2. **Clauses**
   - Clause type (payment terms, liability, termination, etc.)
   - Clause text
   - Page number
   - Risk level (low, medium, high)

3. **Risks**
   - Risk description
   - Severity (low, medium, high, critical)
   - Related clause
   - Mitigation recommendations

4. **Compliance Issues**
   - Regulation (GDPR, CCPA, SOX, etc.)
   - Issue description
   - Severity level

5. **Redlining Suggestions**
   - Original clause text
   - Suggested revised text
   - Rationale for change

### Analysis Result Storage

- Results are stored **in memory** during your session
- Results are **not saved to disk** automatically
- Results are **cleared** when you start a new analysis
- Results remain available for querying until you close the app

---

## Querying Your Contract

### The Chat Interface

After analysis completes, you'll see the **Chat Screen**:

- **Title:** Shows your contract filename
- **Conversation History:** Scrollable area showing all Q&A
- **Query Input:** Multi-line text box for your questions
- **Send Button:** Submit your query
- **New Analysis Button:** Return to upload screen

### Asking Your First Question

1. **Type your question** in the input box at the bottom
2. **Press Enter** or click **"Send"**
3. **Wait** for the response (3-10 seconds)
4. **Read the answer** in the conversation history

### First Query - Model Download

**Important:** The first time you ask a question, CR2A downloads the Pythia AI model:

- **Size:** ~800MB
- **Time:** 15-30 seconds
- **Frequency:** One-time only
- **Location:** Stored locally for future use

**What to expect:**
- Progress indicator during download
- "Loading AI model..." message
- Slightly longer wait time
- All future queries are much faster!

### Example Questions

#### About Parties
```
Who are the parties in this contract?
Who is the buyer?
Who is the seller?
What is the buyer's address?
What company is the vendor?
```

#### About Terms
```
What are the payment terms?
What is the contract duration?
When does the contract start?
When does the contract expire?
What are the termination conditions?
What is the warranty period?
```

#### About Risks
```
What risks are identified in this contract?
What are the high-severity risks?
What financial risks exist?
How can we mitigate the identified risks?
What is the most critical risk?
```

#### About Compliance
```
Are there any GDPR compliance issues?
What compliance issues were found?
Does this contract comply with CCPA?
What regulations apply to this contract?
```

#### About Clauses
```
What clauses are in this contract?
What does the liability clause say?
Where is the payment clause?
What page is the termination clause on?
```

#### About Money
```
What is the total contract value?
What is the payment schedule?
Are there any penalties?
What are the late payment fees?
Is there a deposit required?
```

### Understanding Responses

**Response Format:**
```
You: [Your question]
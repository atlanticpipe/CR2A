# 🚀 Contract Analysis Tool - Self-Contained Installer

## **Single EXE Installation Solution**

This document describes the **self-contained installer** approach that provides a complete Windows 11 installation experience in a single executable file.

---

## **🎯 What You Get**

### **Single File Installation:**
- **File:** `ContractAnalysisSetup.exe`
- **Size:** ~25 MB (includes all dependencies)
- **Function:** Double-click → Automatic installation starts
- **Experience:** Professional installation wizard

### **Installation Features:**
- ✅ **Zero Prerequisites** - Everything included in single EXE
- ✅ **No Admin Required Initially** - Elevates when needed
- ✅ **No Terminal/PowerShell** - Pure GUI installation experience
- ✅ **Professional UI** - Modern installer with progress indicators
- ✅ **Complete Integration** - Desktop shortcuts, Start Menu, file associations
- ✅ **Enterprise Ready** - Registry integration and uninstaller

---

## **📋 Installation Process**

### **For End Users (Windows 11):**

#### **Step 1: Get the Installer**
```cmd
# Download from GitHub repository
# File: ContractAnalysisSetup.exe
```

#### **Step 2: Run Installation**
```cmd
# Simply double-click the EXE file
ContractAnalysisSetup.exe
```

#### **Step 3: Follow Installation Wizard**
1. **Welcome Screen** - Introduction and feature overview
2. **License Agreement** - EULA acceptance
3. **Installation Directory** - Default: `C:\Program Files\Contract Analysis Tool\`
4. **Installation Progress** - Automatic file copy and configuration
5. **Completion** - Launch application or view documentation

#### **Step 4: Configure API Key**
```cmd
# Set environment variable (via installer or manually)
setx OPENAI_API_KEY "sk-your-api-key-here"
```

#### **Step 5: Start Using**
- **Desktop Shortcut:** Double-click "Contract Analysis Tool"
- **Start Menu:** Search for "Contract Analysis Tool"
- **File Association:** Double-click PDF/DOCX files

---

## **🛠️ For Developers: Creating the Self-Contained Installer**

### **Prerequisites:**
- **Windows 11 x64** (for building)
- **Python 3.10+** (with PyInstaller)
- **NSIS** (Nullsoft Scriptable Install System)

### **Build Process:**

#### **Step 1: Setup Environment**
```cmd
# Run the setup script
setup_selfcontained_installer.bat
```

#### **Step 2: Create Installer**
```cmd
# Build the self-contained installer
create_selfcontained_installer.bat
```

#### **Step 3: Distribute**
```cmd
# Copy the single EXE file
copy ContractAnalysisSetup.exe "path\to\distribution\"
```

---

## **📦 Self-Contained Installer Contents**

### **Application Files:**
- `ContractAnalysisApp.exe` - Main application (PyInstaller onefile)
- `output_schemas_v1.json` - JSON Schema validation
- `validation_rules_v1.json` - Company policy rules
- `schemas\` - Schema files directory
- `policy\` - Policy files directory

### **Installation Logic:**
- **Directory Creation** - `C:\Program Files\Contract Analysis Tool\`
- **Shortcut Creation** - Desktop and Start Menu
- **File Associations** - PDF/DOCX integration
- **Registry Entries** - Windows uninstaller integration
- **Uninstaller** - Complete removal capability

### **User Experience:**
- **Modern UI** - Professional installation wizard
- **Progress Indicators** - Visual feedback during installation
- **Error Handling** - Graceful failure recovery
- **Rollback Support** - Installation can be cancelled safely

---

## **🔧 Technical Implementation**

### **NSIS Script Features:**
```nsis
; Self-contained installer with everything included
OutFile "ContractAnalysisSetup.exe"
InstallDir "$PROGRAMFILES64\Contract Analysis Tool"

; Automatic elevation when needed
RequestExecutionLevel user

; Professional UI
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
```

### **Installation Paths:**
```
C:\Program Files\Contract Analysis Tool\
├── ContractAnalysisApp.exe          (main application)
├── output_schemas_v1.json           (schema file)
├── validation_rules_v1.json         (policy file)
├── schemas\                         (schema directory)
├── policy\                          (policy directory)
├── README.txt                       (installation notes)
└── Uninstall.exe                    (uninstaller)
```

### **Registry Integration:**
```reg
HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\ContractAnalysisTool
- DisplayName: "Contract Analysis Tool"
- UninstallString: "C:\Program Files\Contract Analysis Tool\Uninstall.exe"
- Publisher: "Atlantic Pipe Services"
- InstallLocation: "C:\Program Files\Contract Analysis Tool\"
```

---

## **🚀 Usage Instructions**

### **For End Users:**

#### **Installation:**
1. **Download** `ContractAnalysisSetup.exe` from distribution source
2. **Double-click** the EXE file to start installation
3. **Follow prompts** in the installation wizard
4. **Accept license** agreement
5. **Choose directory** (default recommended)
6. **Wait for completion** and click Finish

#### **Post-Installation:**
1. **Set API Key** (if not prompted during installation)
2. **Launch application** from Desktop shortcut
3. **Drag & drop** PDF/DOCX files for analysis
4. **Save results** as PDF reports and JSON data

### **For Administrators:**

#### **Silent Installation:**
```cmd
ContractAnalysisSetup.exe /S
```

#### **Custom Directory:**
```cmd
ContractAnalysisSetup.exe /D=C:\Custom\Install\Path
```

#### **Unattended Setup:**
```cmd
# Pre-configure API key
setx OPENAI_API_KEY "sk-your-key-here"

# Run installer silently
ContractAnalysisSetup.exe /S
```

---

## **🔒 Security & Permissions**

### **Privilege Management:**
- **Initial Launch:** Runs as standard user
- **Installation:** Elevates to administrator when needed
- **File Operations:** Uses appropriate permissions for system directories
- **Registry Access:** Requests elevation for system registry changes

### **File Associations:**
- **PDF Files:** `HKCR\.pdf` → ContractAnalysisTool.Document
- **DOCX Files:** `HKCR\.docx` → ContractAnalysisTool.Document
- **Icons:** Uses application icon for associated files
- **Context Menu:** "Open with Contract Analysis Tool"

---

## **🗑️ Uninstallation**

### **Standard Uninstallation:**
1. **Start Menu:** "Contract Analysis Tool" → "Uninstall"
2. **Control Panel:** Programs and Features → Contract Analysis Tool
3. **Direct:** `C:\Program Files\Contract Analysis Tool\Uninstall.exe`

### **Complete Removal:**
- ✅ **Application Files** - All program files deleted
- ✅ **Shortcuts** - Desktop and Start Menu entries removed
- ✅ **File Associations** - PDF/DOCX associations cleared
- ✅ **Registry Entries** - Uninstaller registry entries removed
- ✅ **User Data** - Log files and settings cleaned up

---

## **🔧 Troubleshooting**

### **Installation Issues:**

**"Installation failed"**
```cmd
# Check Windows version (requires Windows 11)
winver

# Run as administrator if needed
# Right-click → "Run as administrator"
```

**"NSIS not found" (during building)**
```cmd
# Install NSIS from official website
# https://nsis.sourceforge.io/Download

# Verify installation
where makensis
```

**"Python not found" (during building)**
```cmd
# Ensure Python 3.10+ is installed
python --version

# Check PATH includes Python
where python
```

### **Runtime Issues:**

**"OpenAI API key not configured"**
```cmd
# Set environment variable
setx OPENAI_API_KEY "sk-your-key-here"

# Verify setting
echo %OPENAI_API_KEY%
```

**"File association not working"**
```cmd
# Refresh Windows Explorer
taskkill /f /im explorer.exe
start explorer.exe
```

---

## **✅ Verification Checklist**

### **Pre-Installation:**
- [ ] **Windows 11 x64** (`winver` shows Windows 11)
- [ ] **Administrator privileges** (for full installation)
- [ ] **Internet connection** (for API key setup)

### **Installation:**
- [ ] **Installer launches** (double-click works)
- [ ] **Installation completes** (progress bar finishes)
- [ ] **Desktop shortcut created** (visible on desktop)
- [ ] **Start Menu entry exists** (searchable in Start Menu)

### **Post-Installation:**
- [ ] **Application launches** (shortcut works)
- [ ] **API key configured** (environment variable set)
- [ ] **File analysis works** (drag PDF → analyze → save)
- [ ] **Uninstaller available** (in Start Menu and Program Files)

---

## **🎉 Success!**

**Your self-contained Contract Analysis Tool installer is ready!**

### **What You Have:**
- ✅ **Single EXE File** - `ContractAnalysisSetup.exe` with everything included
- ✅ **Automatic Installation** - Double-click to start installation wizard
- ✅ **Professional Experience** - Modern UI with progress indicators
- ✅ **Complete Integration** - Windows 11 shortcuts, associations, uninstaller
- ✅ **Enterprise Ready** - Registry integration and proper permissions

### **Distribution:**
- **File to Distribute:** `ContractAnalysisSetup.exe` (single file)
- **Size:** ~25 MB (includes all dependencies)
- **Platform:** Windows 11 x64
- **Installation:** Automatic when double-clicked

**🎯 Ready for seamless Windows 11 deployment with professional installation experience!**
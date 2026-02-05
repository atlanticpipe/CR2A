# CR2A Code Signing Guide for Internal Use

This guide explains how to sign the CR2A application with a self-signed certificate for internal distribution, eliminating Windows Security warnings without purchasing a commercial certificate.

## Overview

Windows blocks unsigned applications by default. For internal use, you can create a free self-signed certificate and distribute it to your team's machines.

## Quick Start (3 Steps)

### Step 1: Create Certificate (One-time, on build machine)

```powershell
# Run PowerShell as Administrator
.\build_tools\create_self_signed_cert.ps1
```

This creates:
- A code signing certificate in your certificate store
- `cert/CR2A_CodeSigning.cer` - Public certificate (distribute to users)
- `cert/CR2A_CodeSigning.pfx` - Private key backup (keep secure!)

**Save the certificate thumbprint** shown at the end - you'll need it.

### Step 2: Sign the Application (After each build)

```powershell
# Build the application
python build_tools/build.py --target gui

# Sign the executable
.\build_tools\sign_application.ps1

# Rebuild the installer with signed executable
python build_tools/build.py --target installer
```

### Step 3: Install Certificate on User Machines

On each machine that will run CR2A:

```powershell
# Run PowerShell as Administrator (recommended)
.\build_tools\install_cert.ps1
```

Or manually:
1. Double-click `cert/CR2A_CodeSigning.cer`
2. Click "Install Certificate"
3. Choose "Local Machine" (requires admin) or "Current User"
4. Select "Place all certificates in the following store"
5. Click "Browse" → Select "Trusted Root Certification Authorities"
6. Click "Next" → "Finish"
7. Repeat steps 1-6 but select "Trusted Publishers" in step 5

## Detailed Instructions

### Creating the Certificate

The self-signed certificate is valid for 5 years and can sign unlimited applications.

**Requirements:**
- Windows 10/11
- PowerShell (run as Administrator recommended)

**Command:**
```powershell
.\build_tools\create_self_signed_cert.ps1
```

**What it does:**
- Creates a code signing certificate
- Stores it in your Personal certificate store
- Exports public certificate for distribution
- Exports private key backup (password protected)

**Important:**
- Keep the `.pfx` file secure - it contains your private key
- Back up the `.pfx` file - you'll need it if you rebuild your machine
- The password you set protects the private key

### Signing the Application

After building the application, sign it before creating the installer.

**Command:**
```powershell
.\build_tools\sign_application.ps1
```

**Options:**
```powershell
# Specify executable path
.\build_tools\sign_application.ps1 -ExePath ".\dist\CR2A\CR2A.exe"

# Specify certificate thumbprint
.\build_tools\sign_application.ps1 -CertThumbprint "YOUR_THUMBPRINT_HERE"
```

**What it does:**
- Finds your code signing certificate
- Signs the CR2A.exe file
- Adds a timestamp (proves when it was signed)

**Verification:**
Right-click `CR2A.exe` → Properties → Digital Signatures tab
You should see your certificate listed.

### Installing Certificate on User Machines

Each user needs the certificate installed to trust your signed applications.

**Method 1: Automated Script (Recommended)**
```powershell
# As Administrator (machine-wide)
.\build_tools\install_cert.ps1

# As regular user (current user only)
.\build_tools\install_cert.ps1
```

**Method 2: Group Policy (Enterprise)**
For organizations with Active Directory:
1. Copy `CR2A_CodeSigning.cer` to a network share
2. Use Group Policy to deploy to "Trusted Root Certification Authorities"
3. Use Group Policy to deploy to "Trusted Publishers"

**Method 3: Manual Installation**
See Step 3 in Quick Start above.

## Complete Build & Sign Workflow

```powershell
# 1. Clean build
Remove-Item -Recurse -Force dist\CR2A -ErrorAction SilentlyContinue

# 2. Build application
python build_tools/build.py --target gui

# 3. Sign executable
.\build_tools\sign_application.ps1

# 4. Build installer
python build_tools/build.py --target installer

# 5. Distribute
# - dist/CR2A_Setup.exe (installer)
# - cert/CR2A_CodeSigning.cer (certificate for users)
```

## Troubleshooting

### "No code signing certificates found"
**Solution:** Run `create_self_signed_cert.ps1` first to create a certificate.

### "Certificate not trusted" warning still appears
**Solution:** Install the certificate on the user's machine using `install_cert.ps1`.

### "Access denied" when installing certificate
**Solution:** Run PowerShell as Administrator.

### Certificate expired
**Solution:** Create a new certificate (valid for 5 years) and re-sign the application.

### Lost certificate or rebuilt machine
**Solution:** Import the `.pfx` backup file:
```powershell
Import-PfxCertificate -FilePath ".\cert\CR2A_CodeSigning.pfx" -CertStoreLocation Cert:\CurrentUser\My
```

## Security Considerations

### For Internal Use Only
- Self-signed certificates are **not trusted by default** on other machines
- They are perfect for internal/organizational use
- They do **not** provide the same trust as commercial certificates

### Best Practices
1. **Protect the private key** (`.pfx` file)
   - Store in a secure location
   - Use a strong password
   - Don't share publicly

2. **Distribute certificate securely**
   - Use internal network shares
   - Email to trusted recipients only
   - Use Group Policy for enterprise deployment

3. **Document certificate thumbprint**
   - Keep a record of which certificate signed which version
   - Helps with troubleshooting

4. **Renew before expiration**
   - Certificates are valid for 5 years
   - Set a reminder to renew before expiration

## Alternative: Commercial Certificate

For external distribution or higher trust, consider purchasing a commercial code signing certificate:

**Providers:**
- DigiCert: ~$474/year
- Sectigo: ~$179/year  
- GlobalSign: ~$249/year

**Benefits:**
- Trusted by all Windows machines by default
- No certificate distribution needed
- Better reputation with Windows SmartScreen

**Process:**
1. Purchase certificate from provider
2. Receive `.pfx` file
3. Use same signing scripts with commercial certificate

## Files Created

```
cert/
├── CR2A_CodeSigning.cer    # Public certificate (distribute to users)
└── CR2A_CodeSigning.pfx    # Private key backup (keep secure!)

build_tools/
├── create_self_signed_cert.ps1  # Create certificate
├── sign_application.ps1         # Sign executable
└── install_cert.ps1             # Install on user machines
```

## Support

If you encounter issues:
1. Check Windows Event Viewer → Application logs
2. Verify certificate is in correct store: `certmgr.msc`
3. Ensure certificate hasn't expired
4. Try re-signing the application

## Summary

**For the developer (one-time setup):**
1. Create certificate: `.\build_tools\create_self_signed_cert.ps1`
2. Sign after each build: `.\build_tools\sign_application.ps1`

**For each user (one-time setup):**
1. Install certificate: `.\build_tools\install_cert.ps1`
2. Run CR2A without warnings

**Cost:** $0 (completely free for internal use)

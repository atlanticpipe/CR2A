# OpenAI API Key Setup Guide

## Quick Setup (Recommended)

### Option 1: PowerShell Script (Works Immediately)

Run this command in PowerShell, replacing `YOUR_KEY` with your actual API key:

```powershell
.\set_api_key.ps1 "sk-your-actual-key-here"
```

**Advantages:**
- ✅ Works immediately in current terminal
- ✅ Also sets permanently for future sessions
- ✅ No need to restart terminal

**Example:**
```powershell
.\set_api_key.ps1 "sk-proj-abc123xyz..."
```

---

### Option 2: Batch Script (Requires Restart)

Run this command in Command Prompt:

```cmd
set_api_key.bat "sk-your-actual-key-here"
```

**Note:** You must restart your terminal after running this.

---

### Option 3: Manual Setup

#### Windows (PowerShell):
```powershell
# Set for current session only
$env:OPENAI_API_KEY = "sk-your-actual-key-here"

# Set permanently (requires restart)
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-actual-key-here", "User")
```

#### Windows (Command Prompt):
```cmd
REM Set permanently (requires restart)
setx OPENAI_API_KEY "sk-your-actual-key-here"
```

---

## Verify API Key is Set

### Check in Current Session:
```powershell
echo $env:OPENAI_API_KEY
```

Should display your API key (starting with `sk-`)

### Check Permanent Setting:
```powershell
[System.Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User")
```

Should display your API key

---

## Get Your API Key

1. Go to: https://platform.openai.com/api-keys
2. Sign in to your OpenAI account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Use one of the setup methods above

---

## Troubleshooting

### "API key not configured" Error

**Problem:** The application can't find your API key.

**Solutions:**

1. **If you just set the key:**
   - Use the PowerShell script (Option 1) - works immediately
   - OR restart your terminal/IDE after using setx

2. **Verify key is set:**
   ```powershell
   echo $env:OPENAI_API_KEY
   ```
   Should show your key, not blank

3. **Set for current session only (quick test):**
   ```powershell
   $env:OPENAI_API_KEY = "sk-your-key-here"
   python main.py
   ```

### "Invalid API key format" Error

**Problem:** Your API key doesn't start with `sk-`

**Solution:** 
- Verify you copied the complete key from OpenAI
- API keys should look like: `sk-proj-abc123...` or `sk-abc123...`
- Don't include quotes when copying

### Key Works in One Terminal But Not Another

**Problem:** Environment variable not set permanently

**Solution:**
- Use the PowerShell script: `.\set_api_key.ps1 "your-key"`
- OR use setx and restart ALL terminals

---

## Security Best Practices

### ✅ DO:
- Keep your API key secret
- Use environment variables (not hardcoded)
- Rotate keys periodically
- Use different keys for dev/prod

### ❌ DON'T:
- Commit API keys to git
- Share keys in screenshots
- Hardcode keys in source files
- Use production keys for testing

---

## Quick Reference

### Set Key (PowerShell - Immediate):
```powershell
.\set_api_key.ps1 "sk-your-key"
```

### Set Key (Current Session Only):
```powershell
$env:OPENAI_API_KEY = "sk-your-key"
```

### Check Key:
```powershell
echo $env:OPENAI_API_KEY
```

### Run Application:
```powershell
python main.py
```

---

## After Setting the Key

Once your API key is set, you can:

1. **Run the desktop application:**
   ```powershell
   python main.py
   ```

2. **Run the API server:**
   ```powershell
   python contract_analysis_api.py
   ```

3. **Validate everything:**
   ```powershell
   python validate_fixes.py
   ```

---

## Need Help?

If you're still having issues:

1. Run validation script:
   ```powershell
   python validate_fixes.py
   ```

2. Check error.log:
   ```powershell
   type error.log
   ```

3. Verify Python can see the key:
   ```powershell
   python -c "import os; print('Key set:', bool(os.getenv('OPENAI_API_KEY')))"
   ```

---

**Recommended:** Use the PowerShell script (`.\set_api_key.ps1`) for the easiest setup!

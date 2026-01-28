# Quick Fix Checklist - Contract Analysis App

## 🚨 CRITICAL FIXES (Do These First!)

### ✅ Step 1: Create Correct Schema File (5 min)
```cmd
# I will create the correct output_schemas_v1.json file for you
# This is the #1 blocking issue
```
**Status:** [ ] Not Started → [ ] In Progress → [ ] Complete

---

### ✅ Step 2: Set API Key (1 min)
```cmd
setx OPENAI_API_KEY "sk-your-actual-openai-key-here"
```
**Then restart your terminal/IDE**

**Status:** [ ] Not Started → [ ] In Progress → [ ] Complete

---

### ✅ Step 3: Install Dependencies (2 min)
```cmd
pip install -r requirements.txt
```

**Status:** [ ] Not Started → [ ] In Progress → [ ] Complete

---

### ✅ Step 4: Test Basic Functionality (2 min)
```cmd
# Test schema loads
python -c "import json; print('Schema OK' if json.load(open('output_schemas_v1.json')) else 'Failed')"

# Test validator
python -c "import validator; validator.load_schema(); print('Validator OK')"

# Test GUI launches
python main.py
```

**Status:** [ ] Not Started → [ ] In Progress → [ ] Complete

---

## 🧹 CLEANUP (Do These Second)

### ✅ Step 5: Delete Redundant Files (5 min)
```cmd
# Delete wrong schema file
del output_schemas.json

# Delete unused files
del validation_rules.json
del section_map.json
del clause_classification.json
del simple_contract_analyzer.py
del api_examples.py
del "Screenshot 2025-10-09 133304.png"
del index.html
del web_contract_analyzer.html
del contract_analyzer_web_gpt5.html
```

**Status:** [ ] Not Started → [ ] In Progress → [ ] Complete

---

### ✅ Step 6: Organize Files (5 min)
```cmd
# Create directories
mkdir installers
mkdir docs
mkdir examples
mkdir tools
mkdir tests

# Move installer files
move *.nsi installers\
move *.spec installers\
move create_installer.bat installers\
move create_selfcontained_installer.bat installers\
move setup_selfcontained_installer.bat installers\
move manual_installer.bat installers\

# Move documentation
move SelfContainedInstaller_README.md docs\
```

**Status:** [ ] Not Started → [ ] In Progress → [ ] Complete

---

## 📝 DOCUMENTATION (Do These Third)

### ✅ Step 7: Create README.md (10 min)
**Status:** [ ] Not Started → [ ] In Progress → [ ] Complete

---

### ✅ Step 8: Create config.json (5 min)
**Status:** [ ] Not Started → [ ] In Progress → [ ] Complete

---

## 🧪 TESTING (Do These Last)

### ✅ Step 9: Run Full Test (10 min)
```cmd
# Test extraction
python extract.py path\to\sample.pdf

# Test full workflow
python main.py
# Drop a PDF file and click "Start Analysis"

# Test API server
python contract_analysis_api.py
# In another terminal:
curl http://localhost:8000/health
```

**Status:** [ ] Not Started → [ ] In Progress → [ ] Complete

---

## 📊 Progress Tracker

- [ ] Critical Fixes Complete (Steps 1-4)
- [ ] Cleanup Complete (Steps 5-6)
- [ ] Documentation Complete (Steps 7-8)
- [ ] Testing Complete (Step 9)
- [ ] Application Working ✅

---

## 🎯 Success Criteria

Application is working when:
- [x] GUI launches without errors
- [x] File drop accepts PDF/DOCX
- [x] Analysis completes successfully
- [x] PDF and JSON outputs generated
- [x] No redundant files in root
- [x] Clear error messages for missing config

---

## ⏱️ Estimated Time

- **Critical Fixes:** 10 minutes
- **Cleanup:** 10 minutes
- **Documentation:** 15 minutes
- **Testing:** 10 minutes
- **Total:** ~45 minutes

---

## 🆘 Quick Troubleshooting

**Error: "File not found: output_schemas_v1.json"**
→ Run Step 1 to create the file

**Error: "OPENAI_API_KEY not set"**
→ Run Step 2 and restart terminal

**Error: "No module named 'openai'"**
→ Run Step 3 to install dependencies

**GUI doesn't launch**
→ Check Python version: `python --version` (need 3.10+)

**Analysis fails**
→ Check API key is valid and has credits

---

## 📞 Need Help?

1. Check `IMPLEMENTATION_PLAN.md` for detailed instructions
2. Review error.log file for detailed error messages
3. Verify all files in checklist exist
4. Ensure environment variables are set correctly

---

**Last Updated:** [Current Date]
**Status:** Ready to implement

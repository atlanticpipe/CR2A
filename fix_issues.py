#!/usr/bin/env python3
"""
CR2A Quick Fix Script
Automatically fixes critical issues found during debugging
"""

import re
from pathlib import Path

def fix_openai_model():
    """Fix invalid OpenAI model name (gpt-5.2 -> gpt-4o-mini)"""
    file = Path("src/services/openai_client.py")
    if not file.exists():
        print("[ERROR] File not found: src/services/openai_client.py")
        return False
    
    content = file.read_text(encoding='utf-8')
    if 'gpt-5.2' in content:
        content = content.replace('gpt-5.2', 'gpt-4o-mini')
        file.write_text(content, encoding='utf-8')
        print("[OK] Fixed OpenAI model name (gpt-5.2 -> gpt-4o-mini)")
        return True
    else:
        print("[SKIP] OpenAI model already correct")
        return True

def fix_gitignore():
    """Remove requirements.txt from .gitignore and add python/"""
    file = Path(".gitignore")
    if not file.exists():
        print("[ERROR] File not found: .gitignore")
        return False
    
    lines = file.read_text(encoding='utf-8').splitlines()
    
    # Remove requirements.txt
    original_count = len(lines)
    lines = [l for l in lines if l.strip() != "requirements.txt"]
    removed = original_count - len(lines)
    
    # Add python/ if not present
    if "python/" not in lines:
        lines.append("python/")
        added = True
    else:
        added = False
    
    file.write_text("\n".join(lines) + "\n", encoding='utf-8')
    
    if removed > 0:
        print(f"[OK] Removed 'requirements.txt' from .gitignore")
    if added:
        print(f"[OK] Added 'python/' to .gitignore")
    
    if removed == 0 and not added:
        print("[SKIP] .gitignore already correct")
    
    return True

def fix_typo():
    """Fix POENAI_MAX_OUTPUT_TOKENS typo"""
    file = Path("src/services/openai_client.py")
    if not file.exists():
        print("[ERROR] File not found: src/services/openai_client.py")
        return False
    
    content = file.read_text(encoding='utf-8')
    if 'POENAI_MAX_OUTPUT_TOKENS' in content:
        content = content.replace('POENAI_MAX_OUTPUT_TOKENS', 'OPENAI_MAX_OUTPUT_TOKENS')
        file.write_text(content, encoding='utf-8')
        print("[OK] Fixed typo (POENAI -> OPENAI)")
        return True
    else:
        print("[SKIP] Typo already fixed")
        return True

def add_missing_import():
    """Add missing ClientError import to main.py"""
    file = Path("src/api/main.py")
    if not file.exists():
        print("[ERROR] File not found: src/api/main.py")
        return False
    
    content = file.read_text(encoding='utf-8')
    
    # Check if already imported
    if 'from botocore.exceptions import ClientError' in content:
        print("[SKIP] ClientError import already present")
        return True
    
    # Find boto3 import line and add after it
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith('import boto3'):
            lines.insert(i + 1, 'from botocore.exceptions import ClientError')
            content = '\n'.join(lines)
            file.write_text(content, encoding='utf-8')
            print("[OK] Added missing ClientError import")
            return True
    
    print("[WARN] Could not find boto3 import to add ClientError after")
    return False

def fix_env_template():
    """Fix OpenAI model in .env.template"""
    file = Path(".env.template")
    if not file.exists():
        print("[ERROR] File not found: .env.template")
        return False
    
    content = file.read_text(encoding='utf-8')
    if 'gpt-5.2' in content:
        content = content.replace('gpt-5.2', 'gpt-4o-mini')
        file.write_text(content, encoding='utf-8')
        print("[OK] Fixed OpenAI model in .env.template")
        return True
    else:
        print("[SKIP] .env.template already correct")
        return True

def main():
    print("=" * 60)
    print("CR2A Quick Fix Script")
    print("=" * 60)
    print()
    
    fixes = [
        ("OpenAI Model Name", fix_openai_model),
        (".gitignore", fix_gitignore),
        ("Environment Variable Typo", fix_typo),
        ("Missing Import", add_missing_import),
        (".env.template", fix_env_template),
    ]
    
    results = []
    for name, func in fixes:
        print(f"\n[{name}]")
        try:
            success = func()
            results.append((name, success))
        except Exception as e:
            print(f"[ERROR] Error: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {name}")
    
    print()
    print(f"Fixed: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("\n[SUCCESS] All automatic fixes applied successfully!")
    else:
        print("\n[WARNING] Some fixes failed - review errors above")
    
    print("\n" + "=" * 60)
    print("Manual Fixes Still Required:")
    print("=" * 60)
    print("1. Fix indentation in src/services/openai_client.py (lines 395-410)")
    print("   - Unindent the code block by one level (4 spaces)")
    print("   - Lines starting with 'refined[\"SECTION_I\"]' should align with")
    print("     the 'try' statement, not be inside it")
    print()
    print("2. Install dependencies:")
    print("   pip install -r requirements.txt")
    print()
    print("3. Create .env file from .env.template:")
    print("   copy .env.template .env")
    print("   # Then edit .env with your actual credentials")
    print()

if __name__ == "__main__":
    main()

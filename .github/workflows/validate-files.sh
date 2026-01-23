#!/bin/bash
set -e

echo "Validating required files..."

required_files=(
  "index.html"
  "app_integrated.js"
  "CNAME"
)

required_dirs=(
  "frontend"
  "config"
)

missing_files=()

# Check files
for file in "${required_files[@]}"; do
  if [ ! -f "$file" ]; then
    missing_files+=("$file")
    echo "❌ Missing required file: $file"
  else
    echo "✅ Found: $file"
  fi
done

# Check directories
for dir in "${required_dirs[@]}"; do
  if [ ! -d "$dir" ]; then
    missing_files+=("$dir/")
    echo "❌ Missing required directory: $dir"
  else
    echo "✅ Found: $dir/"
  fi
done

# Validate CNAME format if it exists
if [ -f "CNAME" ]; then
  cname_content=$(cat CNAME | tr -d '\n\r')
  
  # Check for protocol prefixes
  if [[ "$cname_content" =~ ^https?:// ]]; then
    echo "❌ Invalid CNAME format: contains protocol (http:// or https://)"
    echo "   CNAME should contain only the domain name: example.com"
    exit 1
  fi
  
  # Check for trailing slash
  if [[ "$cname_content" =~ /$ ]]; then
    echo "❌ Invalid CNAME format: contains trailing slash"
    echo "   CNAME should contain only the domain name: example.com"
    exit 1
  fi
  
  # Check for paths
  if [[ "$cname_content" =~ / ]]; then
    echo "❌ Invalid CNAME format: contains path"
    echo "   CNAME should contain only the domain name: example.com"
    exit 1
  fi
  
  echo "✅ CNAME format is valid"
fi

# Fail if any files are missing
if [ ${#missing_files[@]} -gt 0 ]; then
  echo ""
  echo "❌ Validation failed! Missing ${#missing_files[@]} required files/directories"
  exit 1
fi

echo ""
echo "✅ All required files present"

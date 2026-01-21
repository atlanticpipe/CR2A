#!/bin/bash
# CR2A v2.0 Deployment to coconuts.velmur.info
# "A coconut is just a nut" - Category Theory joke ¯\_(ツ)_/¯

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║  CR2A v2.0 GitHub Pages Edition                           ║"
echo "║  Deploying to: coconuts.velmur.info                       ║"
echo "║                                                            ║"
echo "║  'A coconut is just a nut' - Math joke for the win! 🥥    ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Confirmation
echo -e "${YELLOW}This will:${NC}"
echo "  1. Create gh-pages branch from current main"
echo "  2. Move webapp files to root"
echo "  3. Create CNAME for coconuts.velmur.info"
echo "  4. Commit and push to GitHub"
echo ""
read -p "Continue? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Deployment cancelled."
    exit 1
fi

echo ""
echo -e "${BLUE}Step 1: Preparing gh-pages branch${NC}"
echo "----------------------------------------"

# Ensure we're in the repo root
if [ ! -d ".git" ]; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

# Check if on main and up to date
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Switching to main branch...${NC}"
    git checkout main
fi

echo "Pulling latest changes..."
git pull origin main

# Check if gh-pages already exists
if git show-ref --verify --quiet refs/heads/gh-pages; then
    echo -e "${YELLOW}gh-pages branch already exists${NC}"
    read -p "Delete and recreate? (y/n): " RECREATE
    if [ "$RECREATE" = "y" ]; then
        git branch -D gh-pages
        echo -e "${GREEN}✓ Deleted old gh-pages branch${NC}"
    else
        echo "Switching to existing gh-pages branch..."
        git checkout gh-pages
    fi
else
    echo "Creating new gh-pages branch..."
    git checkout -b gh-pages
    echo -e "${GREEN}✓ Created gh-pages branch${NC}"
fi

echo ""
echo -e "${BLUE}Step 2: Organizing files${NC}"
echo "----------------------------------------"

# Move webapp to root if it exists
if [ -d "webapp" ]; then
    echo "Moving webapp/ contents to root..."

    # Move all files from webapp to root
    mv webapp/* . 2>/dev/null || true
    mv webapp/.* . 2>/dev/null || true

    # Remove empty webapp directory
    rmdir webapp 2>/dev/null || true

    echo -e "${GREEN}✓ Moved webapp to root${NC}"
else
    echo -e "${YELLOW}ℹ No webapp directory found (already at root?)${NC}"
fi

echo ""
echo -e "${BLUE}Step 3: Creating deployment files${NC}"
echo "----------------------------------------"

# Create CNAME file
echo "coconuts.velmur.info" > CNAME
echo -e "${GREEN}✓ Created CNAME: coconuts.velmur.info${NC}"

# Create/update .gitignore
cat > .gitignore << 'EOF'
# Environment files
.env
.env.local

# API Keys (NEVER commit these!)
**/api-keys.json
**/secrets.json
*.key

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
npm-debug.log*

# Backups
.backups/
*.backup

# Development files (don't deploy)
*.md
!README.md

# Test files
test-*.html
**/tests/
EOF
echo -e "${GREEN}✓ Created .gitignore${NC}"

# Create deployment README
cat > DEPLOYMENT_README.md << 'EOF'
# CR2A v2.0 - GitHub Pages Edition

**Deployed to:** https://coconuts.velmur.info

## About This Deployment

This is the gh-pages branch for CR2A v2.0, which runs entirely client-side with direct OpenAI API integration (no backend required).

### Joke Origin

The subdomain "coconuts" is a category theory math joke. In mathematics, "co-" is used to denote the dual of a concept. When you take the dual twice (co-co-), it's redundant, so a "coconut" is mathematically just a "nut"! 🥥

Source: https://en.wikipedia.org/wiki/Mathematical_joke

## Branch Strategy

- **main branch** → https://velmur.info (v1.x - AWS Lambda version)
- **gh-pages branch** → https://coconuts.velmur.info (v2.0 - GitHub Pages)

## Version Differences

### v2.0 (This Branch - coconuts.velmur.info)
- ✅ Client-side only
- ✅ Direct OpenAI API integration
- ✅ No backend server required
- ✅ PDF export built-in
- ✅ Runs entirely in browser
- ✅ Free hosting on GitHub Pages

### v1.x (Main Branch - velmur.info)
- 🔄 AWS Lambda backend
- 🔄 Server-side processing
- 🔄 Infrastructure costs
- 🔄 More complex deployment

## Deployment

This branch automatically deploys to GitHub Pages when pushed.

To update:
\`\`\`bash
git checkout gh-pages
# Make changes
git add .
git commit -m "Update: description"
git push origin gh-pages
\`\`\`

Changes appear at https://coconuts.velmur.info within 1-2 minutes.

## Configuration

Users configure their own OpenAI API key in the Settings panel. Keys are stored locally in browser localStorage (never transmitted to any server except OpenAI).

## Testing

Before deploying changes, test locally:

\`\`\`bash
python3 -m http.server 8000
\`\`\`

Then visit: http://localhost:8000

## Support

Issues? Check the main repository documentation or contact the development team.
EOF
echo -e "${GREEN}✓ Created DEPLOYMENT_README.md${NC}"

echo ""
echo -e "${BLUE}Step 4: Committing changes${NC}"
echo "----------------------------------------"

# Stage all changes
git add .

# Create commit
COMMIT_MSG="Deploy CR2A v2.0 to coconuts.velmur.info (gh-pages)

- GitHub Pages Edition with client-side OpenAI integration
- No backend required
- PDF export included
- Deployed to: https://coconuts.velmur.info

Branch strategy:
- main → velmur.info (v1.x Lambda version)
- gh-pages → coconuts.velmur.info (v2.0 GitHub Pages)

Math joke: A coconut is just a nut (category theory dual redundancy) 🥥"

git commit -m "$COMMIT_MSG"
echo -e "${GREEN}✓ Changes committed${NC}"

echo ""
echo -e "${BLUE}Step 5: Pushing to GitHub${NC}"
echo "----------------------------------------"

# Push to GitHub
git push -u origin gh-pages

echo -e "${GREEN}✓ Pushed to origin/gh-pages${NC}"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║  ✅ Deployment Script Complete!                           ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo ""
echo "1. Configure GitHub Pages:"
echo "   → Go to: https://github.com/[your-username]/[repo-name]/settings/pages"
echo "   → Source: Deploy from a branch"
echo "   → Branch: gh-pages"
echo "   → Folder: / (root)"
echo "   → Custom domain: coconuts.velmur.info"
echo "   → Click 'Save'"
echo ""
echo "2. Configure DNS (if not already done):"
echo "   → Go to your DNS provider (likely Cloudflare for velmur.info)"
echo "   → Add CNAME record:"
echo "     Type: CNAME"
echo "     Name: coconuts"
echo "     Target: [your-username].github.io"
echo "     Proxy: DNS only (gray cloud)"
echo "     TTL: Auto"
echo ""
echo "3. Wait for DNS propagation (5-15 minutes)"
echo "   → Check: dig coconuts.velmur.info"
echo "   → Or: https://www.whatsmydns.net/#CNAME/coconuts.velmur.info"
echo ""
echo "4. Enable HTTPS (after DNS propagates):"
echo "   → Back in GitHub Pages settings"
echo "   → Wait for green checkmark next to custom domain"
echo "   → Enable 'Enforce HTTPS' checkbox"
echo "   → Certificate generates automatically (5-10 min)"
echo ""
echo "5. Test your deployment:"
echo "   → Visit: https://coconuts.velmur.info"
echo "   → Check browser console for errors (F12)"
echo "   → Test file upload"
echo "   → Configure OpenAI API key in Settings"
echo "   → Run a test analysis"
echo "   → Verify PDF export works"
echo ""
echo -e "${BLUE}Your deployments:${NC}"
echo "   v1.x (Lambda):      https://velmur.info"
echo "   v2.0 (GitHub Pages): https://coconuts.velmur.info 🥥"
echo ""
echo -e "${YELLOW}Pro tip:${NC} The subdomain 'coconuts' is a category theory joke!"
echo "In math, 'co-' means dual. Taking the dual twice (co-co-) is"
echo "redundant, so a 'coconut' is just a 'nut'. Nerdy but fun! 😄"
echo ""
echo "Happy deploying! 🚀"
echo ""

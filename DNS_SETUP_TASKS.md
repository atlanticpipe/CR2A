# DNS Setup Task List for coconuts.velmur.info

## Prerequisites
- [ ] Confirm access to velmur.info DNS management
- [ ] Identify DNS provider (Cloudflare, Route 53, Google Cloud DNS, Name.com, Namecheap, or other)
- [ ] Have GitHub username ready for CNAME target

---

## Phase 1: DNS Configuration

### Option A: Cloudflare (Most Common)
- [ ] Log into Cloudflare dashboard
- [ ] Select velmur.info domain
- [ ] Navigate to DNS → Records
- [ ] Click "Add record"
- [ ] Configure CNAME record:
  - [ ] Type: CNAME
  - [ ] Name: coconuts
  - [ ] Target: [yourusername].github.io
  - [ ] Proxy: DNS only (gray cloud, NOT orange)
  - [ ] TTL: Auto
  - [ ] Comment: CR2A v2.0 GitHub Pages deployment
- [ ] Click "Save"

### Option B: AWS Route 53
- [ ] Go to Route 53 → Hosted Zones → velmur.info
- [ ] Click "Create Record"
- [ ] Configure:
  - [ ] Record name: coconuts
  - [ ] Record type: CNAME
  - [ ] Value: [yourusername].github.io
  - [ ] Routing policy: Simple
- [ ] Click "Save"

### Option C: Google Cloud DNS
- [ ] Go to Cloud DNS → velmur.info
- [ ] Click "Add Record Set"
- [ ] Configure:
  - [ ] DNS Name: coconuts.velmur.info
  - [ ] Resource Record Type: CNAME
  - [ ] Canonical name: [yourusername].github.io
- [ ] Click "Create"

### Option D: Name.com / Namecheap
- [ ] Go to Domain List → velmur.info → Advanced DNS
- [ ] Click "Add New Record"
- [ ] Configure:
  - [ ] Type: CNAME Record
  - [ ] Host: coconuts
  - [ ] Value: [yourusername].github.io
  - [ ] TTL: Automatic
- [ ] Save changes

---

## Phase 2: DNS Verification

### Command Line Verification
- [ ] Open terminal/command prompt
- [ ] Run: `dig coconuts.velmur.info CNAME`
- [ ] Verify output shows: `coconuts.velmur.info. 300 IN CNAME [yourusername].github.io.`
- [ ] Run: `dig coconuts.velmur.info`
- [ ] Verify resolution to GitHub Pages IPs:
  - [ ] 185.199.108.153
  - [ ] 185.199.109.153
  - [ ] 185.199.110.153
  - [ ] 185.199.111.153

### Online Tools Verification
- [ ] Check propagation at: https://www.whatsmydns.net/#CNAME/coconuts.velmur.info
- [ ] Check propagation at: https://dnschecker.org/
- [ ] Verify CNAME record points to [yourusername].github.io
- [ ] Verify all global DNS servers show consistent results

### Wait for Propagation
- [ ] Wait 1-5 minutes (Cloudflare)
- [ ] OR wait 5-60 minutes (other providers)
- [ ] If needed, wait up to 24 hours for full global propagation

---

## Phase 3: GitHub Pages Configuration

- [ ] Go to GitHub repository settings
- [ ] Navigate to Pages section
- [ ] Configure custom domain: coconuts.velmur.info
- [ ] Wait for DNS check to complete
- [ ] Wait for HTTPS certificate to be issued (5-10 minutes)
- [ ] Verify "Enforce HTTPS" is enabled

---

## Phase 4: Testing & Validation

### Basic Connectivity
- [ ] Open browser to: https://coconuts.velmur.info
- [ ] Verify site loads without errors
- [ ] Verify HTTPS certificate is valid (green padlock)
- [ ] Check that URL shows coconuts.velmur.info (not redirected)

### Browser Console Check
- [ ] Open browser developer tools (F12)
- [ ] Check Console tab for errors
- [ ] Verify no 404 errors for resources
- [ ] Verify no CORS errors
- [ ] Verify no mixed content warnings

### Resource Loading
- [ ] Verify CSS loads correctly (styles applied)
- [ ] Verify JavaScript loads correctly (interactive features work)
- [ ] Verify images load correctly (if applicable)
- [ ] Verify fonts load correctly (if applicable)

### Application Functionality
- [ ] Test file upload feature
- [ ] Configure OpenAI API key (if not already set)
- [ ] Test OpenAI API calls work
- [ ] Test PDF export functionality
- [ ] Test all major user workflows

### Cross-Domain Verification
- [ ] Verify https://velmur.info still works (CR2A v1.x)
- [ ] Verify https://coconuts.velmur.info works (CR2A v2.0)
- [ ] Confirm both domains serve different content/versions

---

## Phase 5: Troubleshooting (If Needed)

### If DNS Not Resolving
- [ ] Wait additional 5-15 minutes
- [ ] Clear local DNS cache:
  - [ ] macOS: `sudo dscacheutil -flushcache`
  - [ ] Windows: `ipconfig /flushdns`
  - [ ] Linux: `sudo systemd-resolve --flush-caches`
- [ ] Try using Google DNS (8.8.8.8) for testing
- [ ] Verify CNAME record has no typos
- [ ] Check DNS provider dashboard for record status

### If Certificate Errors
- [ ] Verify CNAME target is: [yourusername].github.io (no /repo path)
- [ ] If using Cloudflare, disable proxy (gray cloud, not orange)
- [ ] Wait 5-10 minutes for GitHub to detect correct DNS
- [ ] Check GitHub Pages settings for DNS verification status
- [ ] Try removing and re-adding custom domain in GitHub

### If Resources Not Loading
- [ ] Check browser console for specific errors
- [ ] Verify all resource paths are relative or use correct domain
- [ ] Check for mixed content (HTTP resources on HTTPS page)
- [ ] Verify CORS headers if loading from external sources
- [ ] Clear browser cache and hard reload (Ctrl+Shift+R)

---

## Final Checklist

- [ ] CNAME record added to velmur.info DNS
- [ ] DNS propagation verified (dig command works)
- [ ] GitHub Pages configured with coconuts.velmur.info
- [ ] HTTPS certificate issued (green padlock)
- [ ] Site loads at https://coconuts.velmur.info
- [ ] No console errors (F12)
- [ ] All resources load (CSS, JS, etc.)
- [ ] File upload works
- [ ] OpenAI API calls work (after key configured)
- [ ] PDF export works

---

## Notes

**Propagation Times:**
- Cloudflare: 1-5 minutes
- Other providers: 5-60 minutes
- Full global propagation: Up to 24 hours (rare)

**Important Reminders:**
- Use DNS only mode (gray cloud) in Cloudflare, NOT proxied (orange cloud)
- CNAME target should be [yourusername].github.io (no repository path)
- Both velmur.info and coconuts.velmur.info should work simultaneously
- They serve different branches: main vs gh-pages

**Fun Fact:**
In category theory, coconut = co(co(nut)) = nut 🥥 = 🌰

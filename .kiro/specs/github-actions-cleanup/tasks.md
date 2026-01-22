# GitHub Actions Cleanup - Implementation Tasks

## Overview
These tasks will clean up the GitHub Actions workflows by removing obsolete and AWS-related files, and fixing the test workflow to match the current repository structure.

## Tasks

- [x] 1. Delete obsolete deployment workflows
  - Delete `.github/workflows/deploy-coconuts.yml` (references deleted `./webapp` directory)
  - Delete `.github/workflows/publish-layers.yml` (AWS Lambda - not used in this version)

- [x] 2. Delete AWS Lambda build action
  - Delete entire `.github/actions/build-layer/` directory and its contents
  - This custom action is only needed for AWS Lambda deployment

- [x] 3. Simplify test workflow to frontend-only
  - Update `.github/workflows/test.yml` to remove all backend-related jobs
  - Keep only the `frontend-tests` job
  - Remove: `backend-tests`, `e2e-tests`, `security-tests`, `performance-tests` jobs
  - Update test commands to match actual package.json scripts:
    - Replace `npm run test:frontend` with `npm test`
    - Remove `npm run test:property` line
    - Keep `npm run test:coverage`
  - Update Node.js version matrix if needed (currently tests on 18, 20, 22)

- [x] 4. Verify deploy-pages.yml is correct
  - Review `.github/workflows/deploy-pages.yml`
  - Confirm it correctly deploys `./frontend` directory to GitHub Pages
  - No changes needed unless issues found

- [x] 5. Test the updated workflows
  - Commit changes to a test branch
  - Verify GitHub Actions run successfully
  - Check that frontend tests execute properly
  - Confirm no errors related to missing files or directories

## Success Criteria

- ✅ All obsolete workflow files removed
- ✅ No AWS-related workflows or actions remain
- ✅ Test workflow only runs frontend tests that exist
- ✅ GitHub Actions pass without errors
- ✅ Frontend deployment to GitHub Pages continues working
- ✅ Repository is cleaner and easier to maintain

## Notes

- This version of CR2A uses only GitHub Pages (frontend) and OpenAI API
- No AWS services (Lambda, S3, etc.) are used in this version
- The Python backend code in `src/` may be for a different architecture

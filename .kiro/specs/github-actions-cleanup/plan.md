# GitHub Actions Cleanup and Fix Plan

## Overview
This plan addresses the GitHub Actions deployment failure caused by references to the deleted `./webapp` directory and fixes other issues in the workflow configurations.

## Problem Summary
- The `deploy-coconuts.yml` workflow references `./webapp` directory which no longer exists
- The `test.yml` workflow references non-existent test directories and Python test files
- The `publish-layers.yml` workflow is for AWS Lambda (NOT NEEDED - this version uses GitHub + OpenAI only)
- The `.github/actions/build-layer/` directory is for AWS Lambda layers (NOT NEEDED)

## Analysis Results

### Files to DELETE
1. `.github/workflows/deploy-coconuts.yml` - References deleted `./webapp` directory
2. `.github/workflows/publish-layers.yml` - AWS Lambda deployment (not used in this version)
3. `.github/actions/build-layer/` - AWS Lambda layer builder (not used in this version)

### Files to KEEP
1. `.github/workflows/deploy-pages.yml` - Frontend deployment to GitHub Pages (NEEDED)

### Files to FIX
1. `.github/workflows/test.yml` - Multiple issues with non-existent test paths

## Executable Tasks

### Task 1: Delete Obsolete Coconuts Deployment Workflow
**Action**: Delete the coconuts deployment workflow that references the deleted webapp directory
**File**: `.github/workflows/deploy-coconuts.yml`
**Reason**: This workflow deploys to coconuts.velmur.info subdomain using the `./webapp` directory which was eliminated from the repository

### Task 2: Delete AWS Lambda Layer Publishing Workflow
**Action**: Delete the Lambda layer publishing workflow
**File**: `.github/workflows/publish-layers.yml`
**Reason**: This version of the app doesn't use AWS services - only GitHub Pages and OpenAI

### Task 3: Delete AWS Lambda Layer Build Action
**Action**: Delete the entire build-layer action directory
**Path**: `.github/actions/build-layer/`
**Reason**: This custom action is only needed for AWS Lambda layer deployment, which this version doesn't use

### Task 4: Review and Update Frontend Deployment Workflow
**Action**: Review `deploy-pages.yml` to ensure it correctly deploys the frontend
**File**: `.github/workflows/deploy-pages.yml`
**Current State**: 
- Triggers on changes to `frontend/**` (✓ correct)
- Uploads `./frontend` directory (✓ correct)
- Deploys to GitHub Pages (✓ correct)
**Changes Needed**: None - workflow is correctly configured

### Task 5: Fix Test Workflow - Remove Backend Tests
**Action**: Update `test.yml` to remove references to non-existent Python backend tests
**File**: `.github/workflows/test.yml`
**Issues**:
- References `tests/backend`, `tests/integration`, `tests/property` directories that don't exist
- References `pytest` commands but no Python test files exist in the repository
- References `tests/performance/locustfile.py` which doesn't exist
- References `src/api/main.py` which doesn't exist
- References AWS/backend services that aren't used in this version

**Changes Needed**:
- Remove `backend-tests` job entirely
- Remove `e2e-tests` job (depends on non-existent backend)
- Remove `security-tests` job (Python-specific, no backend exists)
- Remove `performance-tests` job (references non-existent files)
- Keep only `frontend-tests` job

### Task 6: Simplify Test Workflow for Frontend Only
**Action**: Streamline test.yml to only run frontend tests
**File**: `.github/workflows/test.yml`
**Changes**:
- Keep `frontend-tests` job
- Remove all backend, e2e, security, and performance test jobs
- Update job to only run tests that exist in the repository
- Verify test commands match package.json scripts

### Task 7: Update Test Commands to Match Package.json
**Action**: Update test.yml to use correct npm scripts from package.json
**File**: `.github/workflows/test.yml`
**Current package.json scripts**:
- `npm test` - runs vitest with --run flag
- `npm run test:watch` - runs vitest in watch mode
- `npm run test:coverage` - runs vitest with coverage
- `npm run test:ui` - runs vitest with UI

**Workflow currently uses (INCORRECT)**:
- `npm run test:frontend` - DOES NOT EXIST
- `npm run test:property` - DOES NOT EXIST
- `npm run test:coverage` - EXISTS ✓

**Changes Needed**:
- Replace `npm run test:frontend` with `npm test`
- Remove `npm run test:property` (property tests run with main test command)
- Keep `npm run test:coverage`

## Expected Outcomes

After completing these tasks:
1. ✅ No more deployment failures due to missing `./webapp` directory
2. ✅ No AWS-related workflows (this version uses GitHub + OpenAI only)
3. ✅ GitHub Actions will only run tests that actually exist
4. ✅ Cleaner, more maintainable workflow configurations
5. ✅ Faster CI/CD pipeline (fewer unnecessary jobs)
6. ✅ Frontend deployment continues to work correctly
7. ✅ Reduced repository size (removed unused AWS Lambda action)

## Rollback Plan

If issues occur after changes:
1. Revert commits using `git revert <commit-hash>`
2. Original workflow files are preserved in git history
3. Can restore individual workflows as needed

## Notes

- This version of CR2A uses only GitHub Pages (frontend) and OpenAI API (no AWS services)
- The `publish-layers.yml` workflow and `build-layer` action are remnants from an AWS Lambda version
- Frontend deployment to GitHub Pages should continue working without interruption
- All Python backend code in `src/` appears to be for a different architecture (possibly future AWS version)

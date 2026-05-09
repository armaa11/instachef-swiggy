# TODO

## Step 1: Package mise-en-place into zip (clean, excludes build artifacts)
- [ ] Create zip while excluding: mise-en-place/frontend/.next, mise-en-place/frontend/node_modules, mise-en-place/backend/venv, mise-en-place/backend/__pycache__, any *.env files
- [ ] Place output at: swiggy-build/mise-en-place.zip (contains frontend/ and backend/ at zip root)

## Step 2: Validate zip contents
- [ ] Ensure zip includes: README.md, docker-compose.yml, frontend/package.json, backend/requirements.txt
- [ ] Ensure zip does NOT include excluded artifacts

## Step 3: Final verification
- [ ] Confirm zip file exists and is non-trivial size


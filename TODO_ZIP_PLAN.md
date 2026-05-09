# Zip packaging plan (mise-en-place)

## Information gathered
- Project root is `mise-en-place/`.
- Contains:
  - `frontend/` (Next.js) with `package.json`, `package-lock.json`, TS config, app/ components.
  - `backend/` (FastAPI) with `requirements.txt` and Python app under `backend/app/`.
  - `docker-compose.yml` for Redis.
  - `README.md` with run instructions.
- No `.env` template file detected in the repo.

## Plan
1. Create a zip archive from `mise-en-place/` so another user can download and run it.
2. Exclude common local artifacts if present (e.g. `node_modules`, `.next`, `__pycache__`, `venv`, `*.env`, `package-lock` is kept since it exists).
3. Place the output zip in the parent directory (`swiggy-build/`) as `mise-en-place.zip`.
4. Verify the zip contains expected top-level folders (`frontend/`, `backend/`) and key files (`README.md`, `docker-compose.yml`, `requirements.txt`, `package.json`).

## Dependent files to edit
- None (only generating an archive).

## Followup steps
- User extracts zip.
- User runs backend/frontend commands per `mise-en-place/README.md`.

## <ask_followup_question>
Confirm whether to generate:
- Option A: `mise-en-place.zip` at `swiggy-build/mise-en-place.zip` (recommended)
- Option B: nested zip with root folder included (i.e., zip contains the `mise-en-place/` directory)
</ask_followup_question>


# Shuru

One sentence in, a live website on your own domain out. See `PRD.md` for the product and `architecture.md` for the design.

**Status:** milestone 1 (steps 1 to 3: idea, domain, preview). Nothing in this milestone can spend money. Purchase, hosting, DNS, the launch kit and replay come next.

## Backend

Requires Python 3.12 or newer.

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt 
export ANTHROPIC_API_KEY=...          # read by the Anthropic SDK
export GDDY_PAT=...                   # read by the gddy CLI; gddy must be on PATH
uvicorn app.main:create_default_app --factory --reload
.venv/bin/python -m pytest            # tests use fakes, no external calls
```

Settings come from `SHURU_*` environment variables or `backend/.env` (see `app/config.py`), for example `SHURU_GDDY_ENV` (default `ote`, the test environment) and `SHURU_LOG_LEVEL`.

## Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, forwards /api to the backend on port 8000
npm run build    # typecheck and production build
```

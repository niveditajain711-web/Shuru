# Shuru

One sentence in, a live website on your own domain out. See `PRD.md` for the product and `architecture.md` for the design.

**Status:** milestone 1 (idea, domain, cost review, preview). Nothing in this milestone can spend money. Purchase, hosting, DNS, the launch kit and replay come next.

## Backend

Requires Python 3.12 or newer.

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt 
export ANTHROPIC_API_KEY=...          # read by the Anthropic SDK
export GDDY_PAT=...                   # GoDaddy Personal Access Token, sent as a Bearer token to the v3 REST API
uvicorn app.main:create_default_app --factory --reload
.venv/bin/python -m pytest            # tests use fakes, no external calls
```

Settings come from `SHURU_*` environment variables or `backend/.env` (see `app/config.py`), for example `SHURU_GDDY_READ_BASE_URL` (default `https://api.ote-godaddy.com/v3/domains`, the test environment) and `SHURU_LOG_LEVEL`. If the test environment returns no domain suggestions, set `SHURU_GDDY_READ_BASE_URL=https://api.godaddy.com/v3/domains`: suggest and availability calls are read-only and cannot spend money. The `gddy` CLI is not needed until the hosting step is built.

## Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, forwards /api to the backend on port 8000
npm run build    # typecheck and production build
```

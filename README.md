# Shuru

One sentence in, a live website on your own domain out. See `PRD.md` for the product and `architecture.md` for the design.

**Status:** idea, domain, cost review, preview and purchase. Purchase is in **demo mode** by default (`SHURU_DEMO_MODE=true`), so nothing can spend money until you turn it off. Hosting, DNS, the launch kit and replay come next.

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

Settings come from `SHURU_*` environment variables or `backend/.env` (see `app/core/config.py`), for example `SHURU_GDDY_READ_BASE_URL` (default `https://api.godaddy.com/v3/domains`, production; the test environment `https://api.ote-godaddy.com/v3/domains` returned no domain suggestions) and `SHURU_LOG_LEVEL`. Suggest and availability calls are read-only and cannot spend money. The `gddy` CLI is not needed until the hosting step is built. Each client may start 10 runs per hour (`SHURU_RUN_RATE_LIMIT`, `SHURU_RUN_RATE_WINDOW_SECONDS`); more get a 429, before any Claude call.

**Demo mode and purchasing.** `SHURU_DEMO_MODE` defaults to `true`. The Buy step then asks GoDaddy for a real quote (free) but never calls `POST /v3/domains/registrations`, so nothing is registered or charged, and the screens say so. Quotes need a payment method and registrant contact on the GoDaddy account. Set `SHURU_DEMO_MODE=false` **only** to buy real domains: every confirmed purchase then registers and charges, and anyone holding a run's link can buy (there are no user accounts yet). Quote and registration use `SHURU_GDDY_PURCHASE_BASE_URL` (default production), since a quote token only works where it was issued.

**Contact form mail.** The "Contact us" form emails the Shuru mailbox through GoDaddy's SMTP server. Set these in `backend/.env` (gitignored; see `.env.example`) or the server's environment: `SHURU_SMTP_USER` (the full mailbox address), `SHURU_SMTP_PASSWORD`, and optionally `SHURU_SMTP_HOST` (default `smtpout.secureserver.net`, not `smtp.titan.email`), `SHURU_SMTP_PORT` (default 465; other ports use STARTTLS) and `SHURU_CONTACT_TO`. Never commit the password.

## Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, forwards /api to the backend on port 8000
npm run build    # typecheck and production build
npm test         # unit and integration tests (Vitest, no backend needed)
```

## Deploying to the GoDaddy VPS (shuru.biz)

Target: GoDaddy Gen4 VPS (4 vCPU, 8 GB), Ubuntu 24.04, running Docker. Two containers: `backend` (FastAPI) and `web` (Caddy, which serves the built React app, proxies `/api` to the backend and gets HTTPS certificates automatically). Only ports 80 and 443 are public. Files: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/Caddyfile`.

**Secrets never go in git or in the Docker image.** They live in `backend/.env` on the server (gitignored, `chmod 600`) and reach the container as environment variables.

### 1. Connect with SSH

Get the server's IP and default username (`root` or `ubuntu`) from the GoDaddy VPS dashboard.

```bash
# One-time, on your own machine: create a key. The .pub file is what GoDaddy (or the server) needs.
ssh-keygen -t ed25519 -C "shuru-vps"
cat ~/.ssh/id_ed25519.pub

# Connect (type "yes" to accept the fingerprint the first time)
ssh -i ~/.ssh/id_ed25519 <user>@<server-ip>
cat /etc/os-release          # should say Ubuntu 24.04
```

Optional shortcut in `~/.ssh/config`, then `ssh shuru-vps` is enough:

```
Host shuru-vps
    HostName <server-ip>
    User <user>
    IdentityFile ~/.ssh/id_ed25519
```

Troubleshooting: `Permission denied (publickey)` means the wrong user or the public key is not on the server. `Connection timed out` means port 22 is blocked (check GoDaddy's firewall). `REMOTE HOST IDENTIFICATION HAS CHANGED` after a rebuild: `ssh-keygen -R <server-ip>`. Never commit or share the private key (`id_ed25519`).

### 2. Prepare the server (once)

Run on the server.

```bash

# Install Docker Engine and the compose plugin (official repository)
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 3. Point shuru.biz at the server

In GoDaddy, open the DNS settings for shuru.biz:

- Add or edit an **A** record: Name `@`, Value `<server-ip>`, TTL 600 (replace any parking A record).
- Add a **CNAME** record: Name `www`, Value `@` (or an A record with the same IP).
- **Do not touch the MX, TXT and CNAME records that belong to the Titan mailbox.** Deleting them breaks `nivedita.jain@shuru.biz`.

Check from your machine (it can take a few minutes): `dig +short shuru.biz` should print the server IP. Caddy can only get an HTTPS certificate once this resolves to the server.

### 4. Get the code and the secrets onto the server

```bash
# As deploy, on the server
git clone <repo-url> ~/shuru        # a private repo needs a deploy key or token
cd ~/shuru
git checkout main                   # or the branch you deploy

cp backend/.env.example backend/.env
nano backend/.env                   # fill in the values below
chmod 600 backend/.env
```

`backend/.env` needs: `ANTHROPIC_API_KEY`, `GDDY_PAT`, `SHURU_SMTP_USER` (the full mailbox address), `SHURU_SMTP_PASSWORD`, and `SHURU_CONTACT_TO`. Leave `SHURU_SMTP_HOST=smtpout.secureserver.net` and `SHURU_SMTP_PORT=465`. Type the secrets on the server; do not paste them into chats, commits or issues.

### 5. Build and start

```bash
cd ~/shuru
docker compose up -d --build
docker compose ps                    # both services should be "running"
docker compose logs -f               # Ctrl+C to stop following
```

Open https://shuru.biz. The first request can take a few seconds while Caddy obtains the certificate. Then test the wizard and the Support form (a message should arrive at the mailbox).

### 6. Updating after code changes

```bash
cd ~/shuru
git pull
docker compose up -d --build
```

The run store (SQLite) and the certificates are in Docker volumes, so they survive rebuilds. To change a secret, edit `backend/.env` and run `docker compose up -d --force-recreate backend`.

### Everyday commands

```bash
docker compose logs --tail 100 backend      # backend log (contact mail errors show here)
docker compose restart backend
docker compose down                          # stop (keeps volumes)
docker compose down -v                       # stop AND delete the run store and certificates
docker run --rm -v shuru_shuru_data:/data -v "$PWD":/backup alpine tar czf /backup/shuru-data.tgz -C /data .   # back up the run store
```

### Troubleshooting

- **Site not reachable or certificate error:** the A record does not point at the server yet (`dig +short shuru.biz`), or ports 80 and 443 are blocked in `ufw` or GoDaddy's firewall. Check `docker compose logs web`.
- **Contact form says "couldn't send":** see `docker compose logs backend`. A `535` means a wrong user or password (the user must be the full address, the host `smtpout.secureserver.net`). A timeout means outbound port 465 is blocked: try `SHURU_SMTP_PORT=587`.
- **Domain suggestions are empty:** see `SHURU_GDDY_READ_BASE_URL` above.
- **Local test of the stack:** `SITE_DOMAIN=localhost docker compose up --build` serves https://localhost with a local certificate (your browser will warn).

# Shuru: Architecture

*One sentence in, a live website on your own domain out. Claude does the thinking, GoDaddy makes it real.*

Shuru is an **agentic solution with manual approval gates**, not a fully autonomous agent. The orchestrator (our code) owns the sequence. It calls Claude as a **generator** that returns validated JSON (brief, site, launch kit) and as a **bounded agent** for read-only legwork. The domain scout searches and checks domains with tools until it has good options. Two manual gates (cost review and Approve) stand between the agent's suggestions and anything that spends tokens on the site or money on the domain. The money path stays deterministic, testable and cheap.

> **Status:** milestone 1 (idea, domain, cost review, preview, contact form, per-client rate limits) is built. Shuru runs on the GoDaddy VPS (decided, section 11; first deploy pending). The rest (scout agent, name safety, approval and purchase, hosting, DNS, launch kit, replay) is design. This document is the target architecture; see `LaunchPad Simplified Build Plan.md` for the original plan and schedule (the project was called LaunchPad there).

## 1. Goals and non-goals

**Goals**

- Take a founder from a one-sentence idea to a live URL on a domain they own in about 10 minutes.
- Never spend money without an explicit human approval step.
- Support English and Hindi output.
- Keep the design consistent: Claude fills a fixed template, it does not write arbitrary HTML.
- Stay cheap on Claude credits: one focused call per step, capped `max_tokens`, caching, fixtures.

**Non-goals (for now)**

- A fully autonomous agent. Agent loops are allowed only with read-only tools, a step cap and a budget. Purchase, publishing and DNS are never agent tools and always sit behind Approve.
- Payments, email hosting for users' sites, renewals, domain forwarding, registry lock, contact updates.
- Multi-page sites or user-editable site builders.
- Multi-tenant accounts and auth (a single operator GoDaddy account is assumed).

## 2. System context

```
                +------------------+
   Founder ---> |  React wizard    |  (browser)
                +--------+---------+
                         | HTTPS / JSON
                         v
                +------------------+       +-----------------------+
                |  FastAPI backend | ----> | Claude API (Anthropic)|
                |  (orchestrator,  |       |  generator calls and  |
                |   approval gates)|       |  scout agent (tools)  |
                |                  |       +-----------------------+
                |                  |       +-----------------------+
                |                  | ----> | GoDaddy v3 REST API   |
                |                  |       |  domains, DNS         |
                |                  |       +-----------------------+
                |                  | ----> | GoDaddy Hosting (gddy)|
                +--------+---------+       +-----------------------+
                         |
                         v
                +------------------+
                |  Run store       |  (SQLite)
                +------------------+
```

Shuru has three external dependencies: the **Anthropic API**, the **GoDaddy Domain Lifecycle REST API (v3)**, and a **site publishing target** (GoDaddy Hosting by default, behind an interface so it can be swapped).

## 3. The flow

| # | Step | Actor | Cost | Output |
| --- | --- | --- | --- | --- |
| 1 | Describe idea, pick language | User | none | `idea`, `lang` |
| 2 | **Claude call #1** (brief and name safety) | Backend | low | audience, tone, tagline, 8 to 10 name ideas, per-name safety flags |
| 3 | Domain search and pricing (**scout agent**, planned; fixed search today) | Backend: Claude with read-only GoDaddy tools | low | 5 available domains with prices, reasons and a visible trace |
| 4 | **Choose and review cost (gate 1)** | User | none | one accurate availability re-check, then first-year price, renewal price and a note that taxes and fees are excluded; the user confirms or picks another domain |
| 5 | **Claude call #2** (site content) | Backend | medium | structured JSON: hero, offer, about, FAQ, contact. Runs only after the user confirms the cost in step 4 |
| 6 | Preview | Frontend | none | live render of the template with the JSON |
| 7 | **Approve (gate 2, money gate)** | User | none | explicit approval of domain, price, preview |
| 8 | Quote, purchase | Backend (GoDaddy REST) | **real money** | registered domain |
| 9 | Package, upload, publish site | Backend | none | live site on the publishing target |
| 10 | Connect DNS | Backend (GoDaddy REST) | none | domain resolves to the site |
| 11 | **Claude call #3** (launch kit) | Backend | low | 5 social posts, welcome email, 30-day checklist |

The wizard shows these screens: **Idea, Domain, Review cost, Preview, Confirm**. Steps 8 to 11 run after Confirm, and the same screen polls for progress.

### 3.1 Language: native generation

English and Hindi are both **generated natively by Claude** in Claude call #2, from the same structured brief. Hindi is not machine-translated from the English text.

- **Why:** translated Hindi tends to be stiff and literal. Native generation reads naturally and uses local idiom.
- **Consistency:** both languages come from the same brief and fields (`hero`, `offer`, `about`, `faq`, `contact`), so facts such as prices, place names and contact details must match. Pydantic validation checks that both languages are present for every field, and contact and numeric values are copied from the brief, not regenerated.
- **Quality check:** a native Hindi speaker spot-checks a sample of outputs (tone, honorifics, terms), and a few Hindi outputs are kept as fixtures.
- **Cost:** none extra, since both languages come from one call.

## 4. Components

### 4.1 Frontend (React + Vite)

- Wizard with a **stepper** (Idea, Domain, Review, Preview; a fifth step, Launch, is added with the Confirm screen) that shows done, current and upcoming steps. Finished steps that are still open are clickable; the rest are disabled with a plain-language hint. On narrow screens only the current step keeps its label, with "Step N of 4" above.
- **Navigation lives in the URL hash** (`#/run/{id}/{step}`), with no router library. On load, refresh or browser Back, the frontend fetches the run with `GET /runs/{id}` and opens the step the run's state allows. A step that is locked or not reached yet is replaced in the URL by the step the run is at. The frontend holds only UI state; the run itself is the backend's.
- Step rules mirror the backend state machine: Domain is open until the site is generated, Review only while a domain is chosen, Preview only once the site exists. **Once the site is generated, Domain and Review are locked** (the backend does not allow changing the domain), so Preview offers "Start over".
- **The Shuru logo starts a fresh run.** If a run is on screen it asks for confirmation first; the old run is not deleted and stays reachable by its link or the browser Back button.
- Domain results come from the run (`run.domains`), so returning to the Domain step does not repeat the external search. The Domain step shows a compact business reminder (tagline, name-idea chips, folded details); tapping a chip runs the same keyword search as typing it.
- Preview: the server-rendered site HTML in a sandboxed iframe, with an English/Hindi toggle and "Regenerate (N of 3 left)".
- **Brand and styling:** one stylesheet with design tokens (spacing, type scale, colours) and primary, secondary and subtle button variants. The logo is an inline SVG component (green tile with a "start" arrow, the wordmark, a turmeric dot and "शुरू"), so there are no image assets; it is still a real button that starts a fresh run, and its decorative parts are hidden from screen readers. The palette is green plus one turmeric accent (`#E9A23B`) used only for fills and rings, never for text on white. Secondary text is at least 8:1 contrast and placeholders about 5.8:1. Dark mode is out of scope for now.
- Loading states (spinner and skeletons) announce themselves to screen readers; each new screen moves focus to its heading and updates the page title.
- Review-cost screen (after choosing a domain) shows the domain, first-year price, renewal price and a "taxes and fees not included" note. "Confirm and build my site" is the only way to start Claude call #2; "Pick a different domain" goes back. This is a confirmation of intent, not a purchase.
- Confirm screen shows domain, price, quote expiry countdown and the preview. The Approve button is the only way to trigger step 8.
- **Support modal** (`SupportDialog`, native `<dialog>` with `showModal()` for focus trap, Esc and focus return) opened from a quiet **Support** link in the header; it wraps `ContactForm`. Wizard state lives in `App`, so opening or closing the modal does not touch it. The form posts to `POST /contact`, shows a thank-you or a plain error, and keeps the typed text on failure. It includes a hidden honeypot field. No mail credentials exist in the browser.
- Launch screen polls `GET /runs/{id}` every 2 seconds (see 5.1) and shows the live URL and launch kit.

### 4.2 Backend (Python + FastAPI)

Thin HTTP layer (`routes/`) over a set of services. One endpoint per step, all keyed by `run_id`. Folder responsibilities are in section 12: `core/` (settings, errors, logging), `models/`, `routes/`, `services/`, `clients/` (external APIs), `repositories/` (SQLite) and `utils/`.

| Service | Responsibility |
| --- | --- |
| `claude_service` | The generator Claude calls (brief, site, launch kit). Prompts, model choice, `max_tokens`, prompt caching, Pydantic validation, one retry on invalid JSON. |
| `domain_scout` (planned) | The scout agent: a Claude tool-use loop over a read-only tool allowlist (`suggest_domains`, `check_availability`, both through `domain_service`). Enforces the step cap, token budget, deadline and price ceiling; records the trace on the run; falls back to the fixed search on failure. |
| `name_safety` (planned) | Deny list of famous brands plus the per-name flags from Claude; decides drop, warn or keep. |
| `gddy_client` (in `clients/`) | HTTP client for the GoDaddy v3 REST API (`httpx`): Bearer auth, timeouts, one retry on 429, parses responses, converts minor-unit prices, maps errors to typed exceptions. Only module that calls GoDaddy. |
| `domain_service` | Suggest, availability, quote, purchase. Owns quote-token expiry handling. |
| `site_service` | Renders content JSON through the fixed template to static HTML. |
| `mail_service` | Sends contact-form messages over SMTP (`smtplib`) to the Shuru mailbox. Implicit TLS on port 465, STARTTLS otherwise. Only module that talks SMTP; takes credentials from settings only. |
| `packager` | Wraps the HTML in a minimal Node.js app and zips it to the publishing target's requirements. |
| `publisher` | Interface for publishing a built site (see 4.4). |
| `dns_service` | Adds the DNS records that point the domain at the published site. |
| `run_store` (in `repositories/`) | Persists run state and results in SQLite (stdlib `sqlite3`, one file, WAL mode). |
| `orchestrator` | The fixed state machine that sequences the services and agent steps and enforces the approval gates (section 5). |
| `rate_limit` (in `utils/`) | In-memory per-client sliding-window limits: run creation (10 per hour) and contact (5 per hour). |

### 4.3 Claude usage

| Call | Model | Input | Output (Pydantic model) |
| --- | --- | --- | --- |
| #1 Brief | Haiku 5.5 | idea, lang | `Brief { audience, tone, tagline, names[8..10] }` (planned: per-name safety flags) |
| Scout agent | Haiku 5.5, tool use | brief, lang, price ceiling | `ScoutResult { options[5]: {domain, price, reason}, trace[] }` |
| #2 Site content | Sonnet 5.5 | brief, chosen domain, lang | `SiteContent { hero, offer, about, faq[], contact }` |
| #3 Launch kit | Haiku 5.5 | brief, site content, domain | `LaunchKit { posts[5], welcome_email, checklist[30d] }` |

Rules:

- Claude never decides the flow between steps; the orchestrator does. Generator calls have no tools and return JSON only.
- Only the scout agent has tools, and they are read-only. Tool inputs are validated (domain pattern, TLD list, batch size) before any GoDaddy call, and the loop is capped (8 tool calls, token budget, 30 s).
- Every call sets `max_tokens`. System prompt and site template are cached.
- Output is validated against a Pydantic model; on failure, retry once with the validation error, then fail the step.
- The template, not Claude, owns HTML and CSS. Content is escaped on render.

### 4.4 Site publishing (pluggable)

Publishing sits behind a small interface so the hosting decision can wait:

```python
class Publisher(Protocol):
    def publish(self, site_zip: Path, domain: str) -> PublishResult: ...
    # PublishResult: live_url, dns_records_to_add
```

Planned implementations:

- **GoDaddyHostingPublisher** (default, built later): the v3 domains API has no hosting endpoints, so this is the one place that will use the `gddy` CLI (or another GoDaddy hosting API if one is confirmed). It lives in its own module and is the only code that may spawn processes: `gddy hosting app create`, `source upload`, `subscription attach`, `deployment publish`, polling each operation. Needs a Node.js zip with `package.json` (name, version), `build` and `start` scripts, an app that listens on `PORT`, runtime packages in `dependencies`, and no `node_modules`.
- **StaticHostPublisher** (fallback): a free static host (Cloudflare Pages, Netlify or Vercel) with GoDaddy DNS pointing at it.

### 4.5 Agentic design and approval gates

| Part | Who decides | Tools | Can spend money or change external state? |
| --- | --- | --- | --- |
| Step order | Orchestrator (code) | n/a | n/a |
| Brief, site, launch kit | Claude as generator | none | no |
| Domain scout | Claude as agent | `suggest_domains`, `check_availability` (read-only) | no |
| Gate 1: cost review | User | n/a | releases Claude call #2 (tokens only) |
| Gate 2: Approve | User | n/a | releases quote, purchase, publish, DNS |
| Quote, purchase, publish, DNS | Orchestrator (code) | n/a | yes, only after gate 2 |

The design principle is that the agent finds things and proposes them, people decide, and code acts. Adding a future agent step (for example the post-launch check-up) means adding read-only tools to the allowlist, never write tools.

## 5. Orchestration and state

The orchestrator is a plain state machine, one `run` per founder session.

```
briefed -> domains_listed -> domain_chosen -> site_generated          (built)
   -> approved -> quoted -> purchased -> published -> dns_connected
   -> kit_generated -> complete                                        (planned)
                          (any state) -> failed
```

These are the `RunState` values in `app/models/common.py`; the PRD refers to this list. A run is created already `briefed`, because creation includes Claude call #1.

- `DOMAIN_CHOSEN` is a resting state: choosing a domain only records it (after an accurate availability re-check) and returns the fresh price. Claude call #2 starts only when the user confirms the cost (`POST /runs/{id}/generate`), so tokens are not spent on a domain the user may reject.
- Transitions are only forward and are persisted before the side effect where possible, so a retry can resume.
- **Side-effect steps are idempotent or guarded.** `PURCHASED` is recorded immediately after purchase succeeds, and the purchase step refuses to run if the run is already `PURCHASED`.
- Long operations (hosting upload, publish, DNS propagation) run as background tasks. The frontend polls `GET /runs/{id}`.

### 5.1 Progress updates: polling

Progress is delivered by **polling**, not SSE. The browser calls `GET /runs/{id}` every 1 to 3 seconds (about 2 seconds) and renders `state`, the current step and any `error`.

- **Why:** it is simple behind Caddy on the VPS, survives refreshes and flaky networks, and is easy to test with curl. Updates may lag by up to one interval, which is fine for steps that take seconds to minutes.
- **Requirements:** the endpoint is cheap (a single SQLite read), returns the full current state each time (no event history needed), and the client stops polling at `COMPLETE` or `FAILED`.
- **Later option:** SSE can be added on top of the same run state if the lag becomes a problem, but it needs a host that allows long-lived connections.

### Money gate

1. Nothing in steps 1 to 5 can spend money. `purchase` is only reachable from the `APPROVED` state.
2. `APPROVED` is set only by an explicit `POST /runs/{id}/approve` carrying the exact domain and price the user saw.
3. The backend gets a **fresh quote** right after approval, because quote tokens expire in about 10 minutes. If the quoted price differs from the approved price, the run stops and asks again.
4. Purchase is `POST /registrations` with the `quoteToken` and the accepted agreements, after fetching them for the TLD. It returns 202; the backend polls the registration until `COMPLETED` or `FAILED`.

## 6. API sketch

| Method and path | Purpose |
| --- | --- |
| `POST /runs` | Create a run from `{idea, lang}`; runs Claude call #1; returns brief and names. Rate limited per client (10 per hour; 429 `rate_limited`), checked before the Claude call |
| `GET /runs/{id}/domains` | Suggest domains with indicative prices (or a single user-typed keyword). Planned: runs the scout agent and returns its options and trace on the run |
| `POST /runs/{id}/domain` | Choose a domain; re-checks availability once and refreshes its price; no Claude call; returns the run with the chosen offer |
| `POST /runs/{id}/generate` | User confirmed the cost; triggers Claude call #2; returns site content |
| `GET /runs/{id}/preview` | Rendered HTML (or content JSON) for the preview |
| `POST /runs/{id}/approve` | Money gate; starts purchase, publish, DNS, launch kit as a background job |
| `POST /contact` | Contact form: `{name, email, message, website}` (`website` is a honeypot). Emails the Shuru mailbox; returns `{ok: true}`. 422 invalid, 429 rate limited, 502 SMTP failed, 503 not configured |
| `GET /runs/{id}` | Status, current step, errors, and final results (URL, kit) |
| `POST /runs/{id}/replay` | Replay a cached run from fixtures (demo and offline mode); planned |

Exact shapes will be defined as Pydantic models, shared with the frontend through the generated OpenAPI schema.

## 7. GoDaddy integration

The backend calls the **GoDaddy Domain Lifecycle Management API v3** over HTTPS (spec: `docs/gddy-api-spec.json`). Base URL: `https://api.{env}.com/v3/domains`.

| Step | Endpoint |
| --- | --- |
| Suggest | `GET /suggestions?query=&tlds=&pageSize=` returns `{items: [{domain, inventory, prices[]}]}`; available-only, indicative prices |
| Check | `POST /check-availability` with `{domains: [1..25], optimizeFor: SPEED or ACCURACY}`; per-item `available` or `error` |
| Quote (later) | `POST /registration-quotes` returns a `quoteToken` locking price and agreements for 10 minutes |
| Purchase (later) | `POST /registrations` with the `quoteToken`; 202, then poll `GET /registrations/{id}` |
| DNS (later) | `/zones/{zone}/dns-records` (list, create, replace, delete) |
| Hosting (later) | Not in this API; see 4.4 |

Integration rules:

- **Auth:** a Personal Access Token sent as `Authorization: Bearer <PAT>`, read from `GDDY_PAT` in `backend/.env` by the settings layer. It is never logged or sent to the client.
- **Environments:** read-only calls (suggest, check) and money-moving calls (quote, purchase) have **separate configurable base URLs**. The test environment is `https://api.ote-godaddy.com`; production is `https://api.godaddy.com`. The OTE environment returned an empty body for `/suggestions` when tried, so read-only calls may point at production (they cannot spend money) while purchase stays on OTE until a real run is intended. The active base URLs are logged at startup.
- **Prices:** `price.value` is an integer in minor units (for USD, `919` is $9.19), converted with the currency's ISO-4217 decimals. The 1-year entry (`period == 1`) is used, with `renewalPrice` kept alongside it. Prices exclude taxes and fees and are indicative until a quote.
- **Errors:** responses carry `{name, correlationId, message}` and an `X-Request-Id` header; the correlation id is logged. 401/403 (bad token), 429 (retry once with backoff), timeouts and malformed bodies become a typed `GddyError`. Per-domain check errors (`UNSUPPORTED_TLD`, `INVALID_DOMAIN`, `MISMATCH_FORMAT`) are treated as "not available".
- **Availability policy:** suggestions are trusted as available. One `ACCURACY` check runs on the domain the user chooses. The authoritative check is the quote.
- **Prerequisites on the account:** payment method, registrant contacts, and a hosting plan if using GoDaddy Hosting.

## 8. Data model

Minimal, stored in a single SQLite database:

| Entity | Key fields |
| --- | --- |
| `Run` | `id`, `state`, `lang`, `idea`, `created_at`, `updated_at`, `error` |
| `Brief` | `run_id`, JSON payload |
| `DomainCandidate` | `run_id`, `domain`, `price`, `renewal_price`, `currency`, `chosen`, `reason`, `safety_flag` |
| `AgentTrace` | `run_id`, `step`, tool name, input, result summary, timestamp |
| `Quote` | `run_id`, `domain`, `price`, `token`, `expires_at` |
| `SiteContent` | `run_id`, JSON payload, `template_version` |
| `Deployment` | `run_id`, `publisher`, `live_url`, `operation_ids`, `status` |
| `LaunchKit` | `run_id`, JSON payload |

Quote tokens and PATs are secrets: tokens are never returned to the browser, and the PAT lives only in the environment.

## 9. Error handling and resilience

| Failure | Behaviour |
| --- | --- |
| Claude returns invalid JSON | Retry once with the validation error, then fail the step with a clear message |
| Quote expired or price changed | Re-quote; if the price changed, return to the Confirm screen |
| Purchase unavailable for the account | Stop at the locked quote and show it; allow continuing with an already-owned domain |
| Hosting upload or publish fails | Fall back to `StaticHostPublisher` if configured, otherwise surface the error with retry |
| DNS propagation slow | Show "pending", poll, and keep the run in `DNS_CONNECTED` until the URL resolves |
| Chosen domain no longer available | Chosen domain re-check fails; the user is told and returned to the domain list. No Claude call is made |
| Any GoDaddy request fails, times out or is rate limited | Retry once on 429; otherwise a typed error, run marked `FAILED` at that step, safe to retry the step if it is idempotent |

| Too many runs from one client | 429 `rate_limited` before any Claude call |
| Scout agent hits its cap, budget or deadline | Return the options found so far; if there are none, use the fixed search |

**Replay mode** (planned) opens a saved, successful run and replays it through the same UI. Responses come from stored JSON fixtures instead of Claude and GoDaddy, so it makes no external calls and spends no credits or money. It is the demo fallback if the network or an API fails, a way to work on the UI without spending credits, and the base for repeatable tests. Replayed runs are labelled "Replay", and their Approve cannot buy anything.

## 10. Security and safety

- Spending is gated by explicit approval and a server-side state check, not by UI alone.
- Secrets (`ANTHROPIC_API_KEY`, `GDDY_PAT`, `SHURU_SMTP_PASSWORD`) come from environment variables and are never logged or sent to the client. `.env` is gitignored.
- `gddy_client` sends JSON bodies and query parameters through the HTTP library (never string-built URLs), and validates domains against a strict pattern and the API's limits before use. Only the future hosting module may spawn processes, with argument lists.
- Claude output is treated as untrusted: validated by schema, HTML-escaped by the template, never executed.
- **Prompt injection** (founders' text reaches prompts, and output reaches a public site), defended in layers:
  1. Input limits (500-character idea, keywords limited to the domain-label pattern).
  2. User text wrapped in delimiters (`<idea>…</idea>`), and the system prompt tells Claude to treat it as a business description only, never as instructions. The brief sent to the site call is wrapped the same way (`<brief>`), and any of these tags inside the text are removed so the visitor cannot close the tag early. Built in `services/prompts.py`, tested in `tests/test_prompts.py`.
  3. Schema-only output with length limits; one retry, then fail.
  4. Output checks before saving (built, `services/content_check.py`): every string in the brief and site is scanned for links and bare domains (the run's own domain is allowed), emails, phone numbers (9+ digits, Devanagari included), HTML/script/template code and prompt-like phrases. Problems are reported as field paths ("hero.headline.en contains a link") and handled like invalid JSON: one retry with that feedback, then `ClaudeError`. Logs record only the paths and reasons, never the visitor's text. Tested in `tests/test_content_check.py`.
  5. Jinja autoescape plus a sandboxed preview iframe, so no injected markup runs.
  6. Least privilege: the scout agent has only read-only, validated tools, so a successful injection still cannot buy, publish or change DNS.
  7. No secrets or other users' data in prompts.
  8. A set of injection fixtures in the tests.
- **Name safety:** brand-clash, offensive and misleading names are flagged or dropped, and prohibited business ideas stop the run (PRD, name safety check).
- **Contact form:** the SMTP password is read from settings (`SecretStr`) and never logged or sent anywhere. Mail is built with `EmailMessage`, which rejects line breaks in headers, and name and email are also pattern-checked. From is always the mailbox, the visitor goes in `Reply-To`. Abuse controls: honeypot field, in-memory per-client limit (5 per hour, single process). Behind a reverse proxy the limiter sees the proxy's address unless the proxy forwards the client IP (`uvicorn --proxy-headers --forwarded-allow-ips`), to be set when the VPS proxy is configured.
- Per-client rate limit on run creation (10 per hour, `SHURU_RUN_RATE_LIMIT`), to protect Claude spend and GoDaddy quota. It is in memory, for a single backend process; a shared store would be needed to scale out.
- Spend limit set in the Anthropic Console as a backstop.

## 11. Deployment and hosting

**Decided:** Shuru runs on the **GoDaddy Gen4 Linux VPS (4 vCPU, 8 GB) with Docker**, OS **Ubuntu 24.04 LTS**, at **shuru.biz**. Two containers from `docker-compose.yml`: `backend` (FastAPI via uvicorn, non-root, SQLite in a volume, port 8000 not published) and `web` (Caddy: serves the built React app, proxies `/api/*` to the backend, and obtains HTTPS certificates automatically; also redirects `www`). Only ports 80 and 443 are open (`ufw`). DNS: an A record for `@` and a CNAME for `www`; the Titan mail DNS records must be left alone. The backend runs with `--proxy-headers`, so the contact-form limiter sees the real client IP from Caddy. Step-by-step commands are in the README.

**Secrets on the VPS:** `ANTHROPIC_API_KEY`, `GDDY_PAT` and `SHURU_SMTP_*` are passed at run time (`docker run --env-file /etc/shuru/backend.env`, file readable only by the deploy user, or compose secrets). They are not baked into the image, not copied by `COPY`, and not committed; keep `.env` in `.dockerignore` as well as `.gitignore`.

**Contact mail:** the container needs outbound access to `smtpout.secureserver.net` on port 465 (or 587). Some VPS providers block outbound SMTP ports; if sending fails with a connection timeout, check the firewall first.

How the VPS meets Shuru's needs:

- **Processes:** the FastAPI backend and Caddy (serving the built React app) run as Docker containers.
- **Outbound access:** HTTPS to Anthropic and GoDaddy, and SMTP to `smtpout.secureserver.net`.
- **Hosting step (later):** `gddy` is installed in the backend image, and the container can run it as a subprocess.
- **Storage:** SQLite lives in a Docker volume, so runs survive restarts and redeploys. Replay fixtures are committed to the repo.
- **Secrets:** an env file readable only by the deploy user (see above).
- **Background tasks:** long steps run in the backend process, and the frontend polls for progress.

Local development uses GitHub Codespaces, a Vite dev server and `uvicorn`, with the `ote` environment and fixtures.

## 12. Repository layout

```
shuru/
  architecture.md
  backend/
    app/
      main.py            # FastAPI app factory, wiring, error handlers
      core/              # config.py (Settings), errors.py (typed errors), logging.py
      models/            # Pydantic models: common.py (types, enums), site.py (Claude output, domains),
                         #   run.py (Run + run requests), contact.py (contact request/response)
      routes/            # HTTP layer, mounted under /api: runs.py, contact.py, deps.py (dependencies)
      services/
        orchestrator.py  # state machine
        claude_service.py
        domain_service.py
        site_service.py
        mail_service.py  # SMTP contact mail
        prompts.py
        packager.py      # planned
        publisher/       # planned: Publisher protocol and implementations
        dns_service.py   # planned
      clients/           # gddy_client.py: external API clients
      repositories/      # run_store.py: SQLite persistence
      utils/             # rate_limit.py: in-memory per-client limiter (contact form)
      templates/         # fixed site template(s)
    tests/
    fixtures/            # cached runs for replay
  frontend/
    src/
      main.tsx, App.tsx  # entry point and wizard shell (state lives in App)
      api/               # API client and shared types
      components/
        steps/           # IdeaStep, DomainStep, ReviewStep, PreviewStep
        dialogs/         # ConfirmDialog, SupportDialog
        forms/           # ContactForm
        ui/              # Stepper, Loading, ErrorMessage, ErrorBoundary, Segmented, Logo, BusinessSummary
      hooks/             # useAction
      lib/               # navigation (step rules) and routing (URL hash)
      utils/             # format helpers
      styles/            # global CSS
      *.test.ts(x)       # Vitest, next to the code they cover
  README.md
```

## 13. Testing strategy

- Unit tests for each service with mocked GoDaddy HTTP responses (recorded from real calls) and a fake Claude client.
- Contract tests for Claude output models using recorded fixtures.
- State machine tests, including "purchase cannot run without approval" and "purchase cannot run twice".
- Agent tests with a scripted fake Claude: the tool allowlist (a write tool request is refused), the step cap, the fallback to fixed search, and the trace being recorded.
- Prompt-injection fixtures: hostile ideas must still produce schema-valid, escaped content with no URLs or contact details.
- Rate-limit tests: the run limit blocks before any Claude call and is separate from the contact limit.
- Frontend: unit tests for the navigation rules and route parsing, plus integration tests (Vitest, Testing Library) that render the whole app against a mocked API: the full flow, stepper locking, resume from the URL, the logo confirmation and browser Back.
- An end-to-end run against the GoDaddy test environment, plus one real run with a cheap domain before any demo.

## 14. Open questions

**Open**

- Container builds not yet exercised on the VPS (first deploy pending); no CI/CD, deploys are `git pull` plus `docker compose up -d --build`.
- Confirm the GoDaddy hosting plan supports Node.js apps (Day 1 check). A plan exists, so GoDaddy Hosting is the default and the static-host fallback is only for failures. Details to be explored later.

**Decided**

- Hosting for Shuru itself: **GoDaddy Gen4 VPS with Docker** (section 11). Render, Railway and shared hosting are no longer options.
- Agent model: **agentic with manual approval gates** (section 4.5). Read-only agent tools only; purchase, publish and DNS stay fixed code behind Approve.
- Abuse limits: **per-client limits** on run creation (10 per hour) and contact (5 per hour), in memory.
- Contact form: backend sends mail over SMTP through the GoDaddy Titan mailbox (`smtpout.secureserver.net`, full address as username); password only in the environment.
- Run store: **SQLite**, not JSON files.
- Progress updates: **polling** (section 5.1), not SSE.
- Hindi: **generated natively** by Claude (section 3.1), not translated from English.
- Logo click: **starts a fresh run** (with confirmation); the clickable Idea step is how the user revisits the current summary.
- Preview: **locked** once generated; "Start over" is the way to change the domain. Unlocking later is possible with a small backend change (swap the domain and re-render without calling Claude).
- Navigation: **URL hash** routing, no router library.

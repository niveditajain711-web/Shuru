# Shuru: Architecture

*One sentence in, a live website on your own domain out. Claude does the thinking, GoDaddy makes it real.*

Shuru is a guided wizard, not an autonomous agent. Our code runs a fixed sequence of steps, and Claude is used as a **generator** at three points, each returning validated JSON. This keeps the system deterministic, testable and cheap.

> **Status:** design. No code exists yet. This document is the target architecture; see `LaunchPad Simplified Build Plan.md` for the original plan and schedule (the project was called LaunchPad there).
>
> **Out of scope for now:** where Shuru itself is hosted and deployed. Section 11 lists the constraints that decision will have to satisfy.

## 1. Goals and non-goals

**Goals**

- Take a founder from a one-sentence idea to a live URL on a domain they own in about 10 minutes.
- Never spend money without an explicit human approval step.
- Support English and Hindi output.
- Keep the design consistent: Claude fills a fixed template, it does not write arbitrary HTML.
- Stay cheap on Claude credits: one focused call per step, capped `max_tokens`, caching, fixtures.

**Non-goals (for now)**

- Autonomous tool-calling or agent loops.
- Payments, email, renewals, domain forwarding, registry lock, contact updates.
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
                |  (orchestrator)  |       +-----------------------+
                |                  |       +-----------------------+
                |                  | ----> | GoDaddy (via gddy CLI)|
                |                  |       |  domains, DNS, hosting|
                +--------+---------+       +-----------------------+
                         |
                         v
                +------------------+
                |  Run store       |  (SQLite)
                +------------------+
```

Shuru has three external dependencies: the **Anthropic API**, the **GoDaddy `gddy` CLI** (REST API as fallback), and a **site publishing target** (GoDaddy Hosting by default, behind an interface so it can be swapped).

## 3. The flow

| # | Step | Actor | Cost | Output |
| --- | --- | --- | --- | --- |
| 1 | Describe idea, pick language | User | none | `idea`, `lang` |
| 2 | **Claude call #1** (brief) | Backend | low | audience, tone, tagline, 8 to 10 name ideas |
| 3 | Domain search and pricing | Backend (`gddy`) | none | candidate domains with availability and price |
| 4 | **Claude call #2** (site content) | Backend | medium | structured JSON: hero, offer, about, FAQ, contact |
| 5 | Preview | Frontend | none | live render of the template with the JSON |
| 6 | **Approve** (money gate) | User | none | explicit approval of domain, price, preview |
| 7 | Quote, purchase | Backend (`gddy`) | **real money** | registered domain |
| 8 | Package, upload, publish site | Backend | none | live site on the publishing target |
| 9 | Connect DNS | Backend (`gddy`) | none | domain resolves to the site |
| 10 | **Claude call #3** (launch kit) | Backend | low | 5 social posts, welcome email, 30-day checklist |

The wizard shows four screens: **Idea, Domain, Preview, Confirm**. Steps 7 to 10 run after Confirm, and the same screen polls for progress.

### 3.1 Language: native generation

English and Hindi are both **generated natively by Claude** in Claude call #2, from the same structured brief. Hindi is not machine-translated from the English text.

- **Why:** translated Hindi tends to be stiff and literal. Native generation reads naturally and uses local idiom.
- **Consistency:** both languages come from the same brief and fields (`hero`, `offer`, `about`, `faq`, `contact`), so facts such as prices, place names and contact details must match. Pydantic validation checks that both languages are present for every field, and contact and numeric values are copied from the brief, not regenerated.
- **Quality check:** a native Hindi speaker spot-checks a sample of outputs (tone, honorifics, terms), and a few Hindi outputs are kept as fixtures.
- **Cost:** none extra, since both languages come from one call.

## 4. Components

### 4.1 Frontend (React + Vite)

- 4-step wizard with a progress bar; holds only UI state and a `run_id`.
- Live preview: renders the site template client-side from the content JSON, with an English/Hindi toggle.
- Confirm screen shows domain, price, quote expiry countdown and the preview. The Approve button is the only way to trigger step 7.
- Launch screen polls `GET /runs/{id}` every 2 seconds (see 5.1) and shows the live URL and launch kit.

### 4.2 Backend (Python + FastAPI)

Thin HTTP layer over a set of services. One endpoint per step, all keyed by `run_id`.

| Service | Responsibility |
| --- | --- |
| `claude_service` | The three Claude calls. Prompts, model choice, `max_tokens`, prompt caching, Pydantic validation, one retry on invalid JSON. |
| `gddy_client` | Wraps the `gddy` CLI: builds commands, runs them with timeouts, parses JSON output, maps errors. Only module that spawns processes. |
| `domain_service` | Suggest, availability, quote, purchase. Owns quote-token expiry handling. |
| `site_service` | Renders content JSON through the fixed template to static HTML. |
| `packager` | Wraps the HTML in a minimal Node.js app and zips it to the publishing target's requirements. |
| `publisher` | Interface for publishing a built site (see 4.4). |
| `dns_service` | Adds the DNS records that point the domain at the published site. |
| `run_store` | Persists run state and results in SQLite (stdlib `sqlite3`, one file, WAL mode). |
| `orchestrator` | The fixed state machine that sequences the services (section 5). |

### 4.3 Claude usage

| Call | Model | Input | Output (Pydantic model) |
| --- | --- | --- | --- |
| #1 Brief | Haiku 5.5 | idea, lang | `Brief { audience, tone, tagline, names[8..10] }` |
| #2 Site content | Sonnet 5.5 | brief, chosen domain, lang | `SiteContent { hero, offer, about, faq[], contact }` |
| #3 Launch kit | Haiku 5.5 | brief, site content, domain | `LaunchKit { posts[5], welcome_email, checklist[30d] }` |

Rules:

- Claude never decides control flow and has no tools. It returns JSON only.
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

- **GoDaddyHostingPublisher** (default): `gddy hosting app create`, `source upload`, `subscription attach`, `deployment publish`, polling each operation. Needs a Node.js zip with `package.json` (name, version), `build` and `start` scripts, an app that listens on `PORT`, runtime packages in `dependencies`, and no `node_modules`.
- **StaticHostPublisher** (fallback): a free static host (Cloudflare Pages, Netlify or Vercel) with GoDaddy DNS pointing at it.

## 5. Orchestration and state

The orchestrator is a plain state machine, one `run` per founder session.

```
CREATED -> BRIEFED -> DOMAINS_LISTED -> DOMAIN_CHOSEN -> SITE_GENERATED
   -> APPROVED -> QUOTED -> PURCHASED -> PUBLISHED -> DNS_CONNECTED
   -> KIT_GENERATED -> COMPLETE
                          (any state) -> FAILED
```

- Transitions are only forward and are persisted before the side effect where possible, so a retry can resume.
- **Side-effect steps are idempotent or guarded.** `PURCHASED` is recorded immediately after purchase succeeds, and the purchase step refuses to run if the run is already `PURCHASED`.
- Long operations (hosting upload, publish, DNS propagation) run as background tasks. The frontend polls `GET /runs/{id}`.

### 5.1 Progress updates: polling

Progress is delivered by **polling**, not SSE. The browser calls `GET /runs/{id}` every 1 to 3 seconds (about 2 seconds) and renders `state`, the current step and any `error`.

- **Why:** it works on every hosting option still under consideration (Node.js, VPS, shared hosting), survives refreshes and flaky networks, and is easy to test with curl. Updates may lag by up to one interval, which is fine for steps that take seconds to minutes.
- **Requirements:** the endpoint is cheap (a single SQLite read), returns the full current state each time (no event history needed), and the client stops polling at `COMPLETE` or `FAILED`.
- **Later option:** SSE can be added on top of the same run state if the lag becomes a problem, but it needs a host that allows long-lived connections.

### Money gate

1. Nothing in steps 1 to 5 can spend money. `purchase` is only reachable from the `APPROVED` state.
2. `APPROVED` is set only by an explicit `POST /runs/{id}/approve` carrying the exact domain and price the user saw.
3. The backend gets a **fresh quote** right after approval, because quote tokens expire in about 10 minutes. If the quoted price differs from the approved price, the run stops and asks again.
4. Purchase uses `--quote-token <token> --agree --confirm`, after fetching required agreements for the TLD.

## 6. API sketch

| Method and path | Purpose |
| --- | --- |
| `POST /runs` | Create a run from `{idea, lang}`; runs Claude call #1; returns brief and names |
| `GET /runs/{id}/domains` | Suggest and check domains with prices |
| `POST /runs/{id}/domain` | Choose a domain; triggers Claude call #2; returns site content |
| `GET /runs/{id}/preview` | Rendered HTML (or content JSON) for the preview |
| `POST /runs/{id}/approve` | Money gate; starts purchase, publish, DNS, launch kit as a background job |
| `GET /runs/{id}` | Status, current step, errors, and final results (URL, kit) |
| `POST /runs/{id}/replay` | Replay a cached run from fixtures (demo and offline mode) |

Exact shapes will be defined as Pydantic models, shared with the frontend through the generated OpenAPI schema.

## 7. GoDaddy integration

The backend drives the `gddy` CLI. Key commands:

| Step | Command |
| --- | --- |
| Suggest | `gddy domain suggest "<query>" --tlds com,net,io --limit 5` |
| Check | `gddy domain available <domain>` (`--check-type full` for definitive) |
| Quote | `gddy domain quote <domain>` |
| Agreements | `gddy domain agreements --tld <tld>` |
| Purchase | `gddy domain purchase --quote-token <token> --agree --confirm` |
| DNS | `gddy dns list / add / set / delete` (`--dry-run` to preview) |
| Hosting | `gddy hosting app create`, `source upload`, `subscription attach`, `deployment publish` |

Integration rules:

- **Auth:** a Personal Access Token via `GDDY_PAT` (no browser OAuth on a server).
- **Environment:** `ote` (test) by default; `prod` only when explicitly configured. The active environment is logged on every run and shown in the UI when not `prod`.
- **Output:** parse the CLI's JSON output; use `--fields` and `--schema` to keep parsing stable. All calls have timeouts and are wrapped so errors become typed exceptions.
- **Prerequisites on the account:** payment method, registrant contacts (`gddy domain contacts init`), and a hosting plan if using GoDaddy Hosting.
- **Fallback:** if the CLI cannot be installed or a command is missing, `gddy_client` can be reimplemented against the GoDaddy REST API without changing callers.

## 8. Data model

Minimal, stored in a single SQLite database:

| Entity | Key fields |
| --- | --- |
| `Run` | `id`, `state`, `lang`, `idea`, `created_at`, `updated_at`, `error` |
| `Brief` | `run_id`, JSON payload |
| `DomainCandidate` | `run_id`, `domain`, `available`, `price`, `currency`, `chosen` |
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
| Any `gddy` command times out | Typed error, run marked `FAILED` at that step, safe to retry the step if it is idempotent |

Replay mode serves cached successful runs from JSON fixtures, for demos and offline work.

## 10. Security and safety

- Spending is gated by explicit approval and a server-side state check, not by UI alone.
- Secrets (`ANTHROPIC_API_KEY`, `GDDY_PAT`) come from environment variables and are never logged or sent to the client. `.env` is gitignored.
- `gddy_client` builds argument lists, never shell strings, and validates domains and TLDs against a strict pattern before use, to prevent command injection.
- Claude output is treated as untrusted: validated by schema, HTML-escaped by the template, never executed.
- Basic rate limiting per client on run creation, to protect Claude spend and GoDaddy quota.
- Spend limit set in the Anthropic Console as a backstop.

## 11. Deployment and hosting (deferred)

Where Shuru runs is intentionally undecided. Whatever is chosen must:

- Run a Python (FastAPI) process and serve the built React app (or host it separately).
- Install the `gddy` binary at build time (it installs to `~/.local/bin` and does not modify `PATH`), or use the REST API instead.
- Allow outbound HTTPS to Anthropic and GoDaddy, and run subprocesses.
- Provide persistent storage for the run store, or accept SQLite file loss on restart (replay fixtures are committed to the repo).
- Support environment secrets and long-ish background tasks.

Local development uses GitHub Codespaces, a Vite dev server and `uvicorn`, with the `ote` environment and fixtures. Revisit this section once hosting options are evaluated.

## 12. Proposed repository layout

```
shuru/
  architecture.md
  backend/
    app/
      main.py            # FastAPI app and routes
      orchestrator.py    # state machine
      models.py          # Pydantic models (API, Claude output, DB)
      services/
        claude_service.py
        gddy_client.py
        domain_service.py
        site_service.py
        packager.py
        publisher/       # Publisher protocol and implementations
        dns_service.py
      store.py           # run store
      templates/         # fixed site template(s)
    tests/
    fixtures/            # cached runs for replay
  frontend/
    src/                 # wizard, preview, API client
  README.md
```

## 13. Testing strategy

- Unit tests for each service with a fake `gddy` runner and a fake Claude client.
- Contract tests for Claude output models using recorded fixtures.
- State machine tests, including "purchase cannot run without approval" and "purchase cannot run twice".
- An end-to-end run in the `ote` environment, plus one real run with a cheap domain before any demo.

## 14. Open questions

**Open**

- Hosting for Shuru itself (section 11): Node.js or a VPS. To be chosen later.
- Confirm the GoDaddy hosting plan supports Node.js apps (Day 1 check). A plan exists, so GoDaddy Hosting is the default and the static-host fallback is only for failures. Details to be explored later.

**Decided**

- Run store: **SQLite**, not JSON files.
- Progress updates: **polling** (section 5.1), not SSE.
- Hindi: **generated natively** by Claude (section 3.1), not translated from English.

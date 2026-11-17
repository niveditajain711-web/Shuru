# Shuru: Architecture

*One sentence in, a live website on your own domain out. Claude does the thinking, GoDaddy makes it real.*

Shuru is a guided wizard, not an autonomous agent. Our code runs a fixed sequence of steps, and Claude is used as a **generator** at three points, each returning validated JSON. This keeps the system deterministic, testable and cheap.

> **Status:** milestone 1 (idea, domain, cost review, preview) is built; the rest is design. This document is the target architecture; see `LaunchPad Simplified Build Plan.md` for the original plan and schedule (the project was called LaunchPad there).
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
                |                  | ----> | GoDaddy v3 REST API   |
                |                  |       |  domains, DNS         |
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
| 2 | **Claude call #1** (brief) | Backend | low | audience, tone, tagline, 8 to 10 name ideas |
| 3 | Domain search and pricing | Backend (GoDaddy REST) | none | suggested domains with indicative prices |
| 4 | **Choose and review cost** | User | none | one accurate availability re-check, then first-year price, renewal price and a note that taxes and fees are excluded; the user confirms or picks another domain |
| 5 | **Claude call #2** (site content) | Backend | medium | structured JSON: hero, offer, about, FAQ, contact. Runs only after the user confirms the cost in step 4 |
| 6 | Preview | Frontend | none | live render of the template with the JSON |
| 7 | **Approve** (money gate) | User | none | explicit approval of domain, price, preview |
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

- Wizard with a **stepper** (Idea, Domain, Review, Preview) that shows done, current and upcoming steps. Finished steps that are still open are clickable; the rest are disabled with a plain-language hint. On narrow screens only the current step keeps its label, with "Step N of 4" above.
- **Navigation lives in the URL hash** (`#/run/{id}/{step}`), with no router library. On load, refresh or browser Back, the frontend fetches the run with `GET /runs/{id}` and opens the step the run's state allows. A step that is locked or not reached yet is replaced in the URL by the step the run is at. The frontend holds only UI state; the run itself is the backend's.
- Step rules mirror the backend state machine: Domain is open until the site is generated, Review only while a domain is chosen, Preview only once the site exists. **Once the site is generated, Domain and Review are locked** (the backend does not allow changing the domain), so Preview offers "Start over".
- **The Shuru logo starts a fresh run.** If a run is on screen it asks for confirmation first; the old run is not deleted and stays reachable by its link or the browser Back button.
- Domain results come from the run (`run.domains`), so returning to the Domain step does not repeat the external search.
- Preview: the server-rendered site HTML in a sandboxed iframe, with an English/Hindi toggle and "Regenerate (N of 3 left)".
- Loading states (spinner and skeletons) announce themselves to screen readers; each new screen moves focus to its heading and updates the page title.
- Review-cost screen (after choosing a domain) shows the domain, first-year price, renewal price and a "taxes and fees not included" note. "Confirm and build my site" is the only way to start Claude call #2; "Pick a different domain" goes back. This is a confirmation of intent, not a purchase.
- Confirm screen shows domain, price, quote expiry countdown and the preview. The Approve button is the only way to trigger step 8.
- Launch screen polls `GET /runs/{id}` every 2 seconds (see 5.1) and shows the live URL and launch kit.

### 4.2 Backend (Python + FastAPI)

Thin HTTP layer over a set of services. One endpoint per step, all keyed by `run_id`.

| Service | Responsibility |
| --- | --- |
| `claude_service` | The three Claude calls. Prompts, model choice, `max_tokens`, prompt caching, Pydantic validation, one retry on invalid JSON. |
| `gddy_client` | HTTP client for the GoDaddy v3 REST API (`httpx`): Bearer auth, timeouts, one retry on 429, parses responses, converts minor-unit prices, maps errors to typed exceptions. Only module that calls GoDaddy. |
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

- **GoDaddyHostingPublisher** (default, built later): the v3 domains API has no hosting endpoints, so this is the one place that will use the `gddy` CLI (or another GoDaddy hosting API if one is confirmed). It lives in its own module and is the only code that may spawn processes: `gddy hosting app create`, `source upload`, `subscription attach`, `deployment publish`, polling each operation. Needs a Node.js zip with `package.json` (name, version), `build` and `start` scripts, an app that listens on `PORT`, runtime packages in `dependencies`, and no `node_modules`.
- **StaticHostPublisher** (fallback): a free static host (Cloudflare Pages, Netlify or Vercel) with GoDaddy DNS pointing at it.

## 5. Orchestration and state

The orchestrator is a plain state machine, one `run` per founder session.

```
CREATED -> BRIEFED -> DOMAINS_LISTED -> DOMAIN_CHOSEN -> SITE_GENERATED
   -> APPROVED -> QUOTED -> PURCHASED -> PUBLISHED -> DNS_CONNECTED
   -> KIT_GENERATED -> COMPLETE
                          (any state) -> FAILED
```

- `DOMAIN_CHOSEN` is a resting state: choosing a domain only records it (after an accurate availability re-check) and returns the fresh price. Claude call #2 starts only when the user confirms the cost (`POST /runs/{id}/generate`), so tokens are not spent on a domain the user may reject.
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
4. Purchase is `POST /registrations` with the `quoteToken` and the accepted agreements, after fetching them for the TLD. It returns 202; the backend polls the registration until `COMPLETED` or `FAILED`.

## 6. API sketch

| Method and path | Purpose |
| --- | --- |
| `POST /runs` | Create a run from `{idea, lang}`; runs Claude call #1; returns brief and names |
| `GET /runs/{id}/domains` | Suggest domains with indicative prices (or a single user-typed keyword) |
| `POST /runs/{id}/domain` | Choose a domain; re-checks availability once and refreshes its price; no Claude call; returns the run with the chosen offer |
| `POST /runs/{id}/generate` | User confirmed the cost; triggers Claude call #2; returns site content |
| `GET /runs/{id}/preview` | Rendered HTML (or content JSON) for the preview |
| `POST /runs/{id}/approve` | Money gate; starts purchase, publish, DNS, launch kit as a background job |
| `GET /runs/{id}` | Status, current step, errors, and final results (URL, kit) |
| `POST /runs/{id}/replay` | Replay a cached run from fixtures (demo and offline mode) |

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
| `DomainCandidate` | `run_id`, `domain`, `price`, `renewal_price`, `currency`, `chosen` |
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

Replay mode serves cached successful runs from JSON fixtures, for demos and offline work.

## 10. Security and safety

- Spending is gated by explicit approval and a server-side state check, not by UI alone.
- Secrets (`ANTHROPIC_API_KEY`, `GDDY_PAT`) come from environment variables and are never logged or sent to the client. `.env` is gitignored.
- `gddy_client` sends JSON bodies and query parameters through the HTTP library (never string-built URLs), and validates domains against a strict pattern and the API's limits before use. Only the future hosting module may spawn processes, with argument lists.
- Claude output is treated as untrusted: validated by schema, HTML-escaped by the template, never executed.
- Basic rate limiting per client on run creation, to protect Claude spend and GoDaddy quota.
- Spend limit set in the Anthropic Console as a backstop.

## 11. Deployment and hosting (deferred)

Where Shuru runs is intentionally undecided. Whatever is chosen must:

- Run a Python (FastAPI) process and serve the built React app (or host it separately).
- Allow outbound HTTPS to GoDaddy. The `gddy` binary is only needed once the CLI-based hosting publisher is built.
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
    src/                 # wizard screens, stepper, URL routing, API client, tests (Vitest)
  README.md
```

## 13. Testing strategy

- Unit tests for each service with mocked GoDaddy HTTP responses (recorded from real calls) and a fake Claude client.
- Contract tests for Claude output models using recorded fixtures.
- State machine tests, including "purchase cannot run without approval" and "purchase cannot run twice".
- Frontend: unit tests for the navigation rules and route parsing, plus integration tests (Vitest, Testing Library) that render the whole app against a mocked API: the full flow, stepper locking, resume from the URL, the logo confirmation and browser Back.
- An end-to-end run against the GoDaddy test environment, plus one real run with a cheap domain before any demo.

## 14. Open questions

**Open**

- Hosting for Shuru itself (section 11): Node.js or a VPS. To be chosen later.
- Confirm the GoDaddy hosting plan supports Node.js apps (Day 1 check). A plan exists, so GoDaddy Hosting is the default and the static-host fallback is only for failures. Details to be explored later.

**Decided**

- Run store: **SQLite**, not JSON files.
- Progress updates: **polling** (section 5.1), not SSE.
- Hindi: **generated natively** by Claude (section 3.1), not translated from English.
- Logo click: **starts a fresh run** (with confirmation); the clickable Idea step is how the user revisits the current summary.
- Preview: **locked** once generated; "Start over" is the way to change the domain. Unlocking later is possible with a small backend change (swap the domain and re-render without calling Claude).
- Navigation: **URL hash** routing, no router library.

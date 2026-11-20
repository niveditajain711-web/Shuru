# Shuru: Product Requirements Document

| | |
| --- | --- |
| **Status** | Draft v0.5 |
| **Scope** | Hackathon MVP, solo build, 5 days, $100 in Claude credits |
| **Stack** | Python (FastAPI), React (Vite), Anthropic Python SDK (with tool use for the agent steps), GoDaddy v3 REST API (`gddy` CLI later for hosting only) |
| **Runs on** | GoDaddy Gen4 Linux VPS with Docker, at shuru.biz (decided) |
| **Source** | `LaunchPad Simplified Build Plan.md` (the project was called LaunchPad there) |

## 1. Summary

Shuru turns one sentence into a live website on a domain the user owns, in about 10 minutes. A first-time founder types an idea (e.g. "I make homemade achaar in Lucknow and want to sell online"), picks English or Hindi, chooses a domain, previews a generated one-page site, approves the purchase, and gets a live URL and a launch kit.

It is an **agentic solution with manual approval gates**, not a fully autonomous agent:

- **Claude acts as an agent where it is safe.** In bounded, read-only tasks Claude chooses its own next step and calls tools. For example, the domain scout (section 5a) searches and checks domains on its own until it has good, available options.
- **The orchestrator owns the sequence.** Application code decides which step runs next and calls the agent steps when the run needs them. Claude never decides to buy, publish or change DNS.
- **People approve every commitment.** Two manual gates stop the flow. One comes before Claude spends tokens writing the site (cost review). The other comes before anything spends money or changes the outside world (Approve). Write actions are not even in the agent's toolset.

The GoDaddy v3 REST API handles domain search, purchase and DNS. Hosting will use the `gddy` CLI when it is built, because the v3 API has no hosting endpoints.

**Problem:** first-time founders stall between "I have an idea" and "I have a URL". Too many decisions (name, domain, site, copy) and too many tools.

**Pitch:** "Idea to live business in 10 minutes, with AI doing the thinking and GoDaddy making it real. The agent does the legwork, you make the decisions."

## 2. Goals and non-goals

**Goals**

- Go from one sentence to a live site on an owned domain, end to end.
- Never spend money without explicit user approval.
- Produce a consistent, polished site from Claude JSON filling a fixed template.
- Support English and Hindi.
- Keep Claude cost low: one call per step, capped tokens, Haiku where possible.
- Use Claude agentically for bounded, read-only legwork (domain scouting, name safety), with the trace visible to the user.
- Keep the money path deterministic, testable and replayable.

**Non-goals**

- A fully autonomous agent. Claude never purchases, publishes, writes DNS or decides when to spend money; those steps are fixed code behind manual approval.
- Renewals, forwarding, registry lock, contact updates.
- Site editing, CMS, e-commerce, email hosting for users' sites, logo or SEO tools. (Shuru itself has one GoDaddy Titan mailbox that receives its own contact form; see section 3.)
- User accounts, end-user billing, production auth.

## 3. Decisions and assumptions

These replace the earlier open questions. Change any that are wrong.

- **Single operator.** The demo uses the developer's GoDaddy account, payment method and registrant contact details. No end-user accounts.
- **One static page** rendered from one template.
- **Hindi and English** are both **generated natively** by Claude in the single site call, from the same structured brief. Hindi is not translated from the English text, because native output reads more naturally. Facts (prices, places, contact details) must match across languages, and a native speaker spot-checks samples. The toggle costs nothing extra.
- **Models:** Haiku 5.5 for the brief, the domain scout agent, the name safety check and the launch kit. Sonnet 5.5 for the site.
- **Agent boundary:** agent steps get only read-only tools (domain suggest, availability check), a step cap and a token budget. Tools that spend money or change external state are never given to Claude.
- **Regeneration cap:** 3 per run.
- **Agreements:** ICANN agreement text is shown in the UI and must be accepted.
- **Storage:** **SQLite** (decided; no JSON-file store). If the host disk is ephemeral, replay fixtures are committed to the repo.
- **Progress updates:** **polling** (decided). The frontend calls `GET /runs/{id}` about every 2 seconds until the run is `live` or `failed`. SSE is a possible later upgrade, not part of this build.
- **Hosting for Shuru itself (decided):** a **GoDaddy Gen4 Linux VPS (4 vCPU, 8 GB) running Docker**, OS Ubuntu 24.04, domain shuru.biz. Two containers: the FastAPI backend and Caddy (serves the React app, proxies `/api`, provides HTTPS). Dockerfiles, compose file and deploy steps are in the repo (README, architecture section 11). Render and Railway are no longer under consideration.
- **Abuse limits:** each client may start 10 runs per hour (`POST /api/runs`, built) and send 5 contact messages per hour, because each run costs a Claude call.
- **Contact form and mailbox:** Shuru has one GoDaddy Titan mailbox (`nivedita.jain@shuru.biz`, Pro Light plan, created with the `gddy` CLI). The wizard page has a "Contact us" form (name, email, message) whose messages the backend emails to that mailbox over SMTP. The SMTP host is GoDaddy's `smtpout.secureserver.net` (port 465, or 587 with STARTTLS), not `smtp.titan.email`, and the username is the full email address. The mailbox password is **only** in the environment (`SHURU_SMTP_PASSWORD`: gitignored `backend/.env` locally, a secret or env file on the VPS), never in code, the repo, the image or the browser. Sites Shuru generates do not get contact forms yet (their `contact` section is display text only).
- **GoDaddy hosting plan:** the account has one, so GoDaddy Hosting is the default publishing target and the static-host fallback is only for failures.
- **Approval** is the Approve click on step 4, with no separate authentication. Until Approve exists, the Buy step's agreement ticks and confirm button are the approval for the purchase.
- **Demo mode for the purchase:** `SHURU_DEMO_MODE` defaults to on. The quote is real, `POST /registrations` is skipped, and the UI says nothing is charged. This lets the whole flow be shown and tested without buying a domain. A real purchase needs `SHURU_DEMO_MODE=false`. The price and consent shown are never faked: the price is always the real quote.
- **GoDaddy access:** REST calls with the PAT as a Bearer token. Read-only calls (suggest, availability) and money-moving calls (quote, purchase) have separate base URLs (`SHURU_GDDY_READ_BASE_URL`, `SHURU_GDDY_PURCHASE_BASE_URL`; both default to production today). The test environment is `https://api.ote-godaddy.com`; its `/suggestions` returned an empty body when tried. A quote token only works in the environment that issued it, so the quote and the registration always share one base URL. Prices come back as integer minor units (`919` = $9.19).
- **Availability policy:** suggestions are trusted as available; one accurate availability check runs on the chosen domain; the quote is the authoritative check.
- **Cost transparency before generation:** after choosing a domain the user sees first-year price, renewal price and a "taxes and fees not included" note, and must confirm before Claude generates the site.
- **Template** is neutral; no brand styling required.
- **UI decisions:** the logo starts a fresh run (with confirmation); the domain is locked once the site is generated (Preview and Buy stay open, with "Start over"); navigation is stored in the URL hash.

Still to verify: before the hosting step, that the backend host can install `gddy` (see section 9).

## 4. User flow

| # | Step | User does | System does |
| --- | --- | --- | --- |
| 1 | Describe idea | Types a sentence, picks language | Claude call 1: brief, name ideas and name safety check |
| 2 | Pick domain | Watches the scout's progress, chooses a domain, reviews its cost, confirms (**gate 1**) | Domain scout agent (read-only tools), accurate re-check of the chosen domain, then (after confirmation) Claude call 2 |
| 3 | Preview site | Reads site, toggles language, may regenerate | Site JSON rendered in template |
| 4 | Confirm and launch | Reviews domain, price, preview; clicks **Approve** (**gate 2**) | Quote, purchase, package, publish, DNS, then Claude call 3: launch kit |

Step 4 is built in slices. **Built so far: the Buy step (quote and purchase), in demo mode by default** (see "Step 4a"). Package, publish, DNS and the launch kit are still planned.

## 5. Functional requirements

### Step 1: Idea and brief

- Input is 1 to 500 characters plus `en` or `hi`. Empty input is rejected by UI and API.
- Claude (Haiku) returns a JSON brief: `audience`, `tone`, `tagline`, and 8 to 10 `name_ideas`.
- The brief is validated with Pydantic. On failure, retry once, then show a "Try again" error.
- The brief is shown to the user before the domain step.
- The idea passes the input rules in section 8a (prompt-injection safeguards) before it reaches Claude.

### Name safety check (planned)

Before a name is shown or searched, Claude checks it, and the result is advisory.

- **Business idea:** if the idea is clearly for something illegal or prohibited (weapons, drugs, counterfeit goods, adult content), the run stops with a polite message and makes no domain or site calls.
- **Each name idea and scout candidate** is flagged if it matches or closely imitates a well-known brand or trademark ("nikeshoes", "amazonpickles"), is offensive in English or Hindi, or is misleading (for example "gov", "official" or a bank name for an unrelated business).
- Clear famous-brand clashes are dropped. Borderline names stay visible with a short warning ("This may be close to an existing brand. Check before you buy.").
- Done in the same Haiku call as the brief (a `flags` field per name) and in the scout agent's final answer, so it costs no extra call. A small built-in deny list of famous brands backs it up without any Claude call.
- It is not legal advice, and the UI says so. The user still decides.

### Step 2: Domains and cost review

- *Built today:* call `GET /suggestions` (`tlds=com,net,io`, small `pageSize`) for the first few brief names. Merge and de-duplicate. Suggestions are available-only and carry indicative 1-year and renewal prices.
- Show the suggestions with their 1-year price. The default search covers only the first few brief names, so every name idea is also shown as a tappable chip: tapping one searches for it, and tapping it again returns to the default list. A typed keyword ("Looking for something else?") goes through suggest the same way. If nothing is found, the user is asked to try a different word.
- Keep the business reminder (tagline, name ideas, folded audience and tone) visible at the top of the step so the user does not have to go back to the Idea screen.
- When the user chooses a domain, run one `POST /check-availability` with accurate checking (`ACCURACY`). If the domain is no longer available, tell the user and return to the list; no Claude call is made.
- **Cost review.** Show the domain, first-year price, renewal price, any premium-domain fee, and the note "Prices exclude taxes and fees and may change until you purchase". Two actions: **Confirm and build my site** and **Pick a different domain**.
- Claude call 2 (the site) runs only after Confirm (**gate 1**). Nothing is purchased in this step.
- Prices are converted from minor units using the currency's decimals.
- All GoDaddy calls go through one client module.

### 5a. Domain scout agent (planned)

This agent replaces the fixed "first few names" search with Claude doing the legwork.

- **Tools (read-only allowlist):** `suggest_domains(query, tlds)` and `check_availability(domains)`, which call the existing GoDaddy client. Nothing else.
- **Loop:** Claude gets the brief, tries names, sees which are taken or expensive, refines (for example "achaar" to "lucknowachaar" or a `.in`), and stops when it has 5 available, affordable options with a one-line reason each. The name safety check applies to every candidate.
- **Limits:** at most 8 tool calls, a token budget, a 30-second deadline and a price ceiling from settings. When a limit is hit, it returns what it has. If the agent fails, the step falls back to today's fixed search.
- **Visible trace:** the Domain step shows the steps live ("Tried lucknowachaar.com: taken. Trying lucknowachaar.in…"), and every tool call is logged with the run.
- **No spending:** the agent only proposes. The user chooses, and the cost review (gate 1) and Approve (gate 2) stay manual.

### Step 3: Site and preview

- Claude (Sonnet) returns site JSON: `hero`, `offer`, `about`, `faq` (3 to 5 items), `contact` (display fields only), with English and Hindi text, each generated natively (not translated).
- Validate with Pydantic. Retry once on failure.
- One HTML template renders the JSON and is the only source of layout and style.
- Live preview in the wizard, language toggle, regenerate (capped).

### Step 4a: Buy the domain (built)

A fifth wizard step, **Buy**, opens from the Site screen's **Buy domain** button. It is the first slice of step 4 and the point where the user approves the money, so it works as the purchase part of gate 2. When hosting and DNS are built, this approval is extended to cover them (see step 4).

1. **Quote.** On opening, `POST /registration-quotes` locks the price (free). The screen shows the domain, price for the period, any premium-domain fee, renewal price, when the lock ends, and the note that ICANN fees and taxes are added at purchase. If the price differs from the one shown at cost review, say so.
2. **Agreements.** List the agreements the quote requires, each linking to its full text. The Buy button stays disabled until the user ticks "I have read and agree". A premium domain has a second tick for its one-time fee.
3. **Purchase.** Only after those ticks, and only if the quote is still locked, `POST /registrations` is called with the quote token, the accepted agreements and the time of consent. The server rejects the purchase if the accepted agreements or price do not match the stored quote.
4. **Outcome.** A completed purchase shows a confirmation and the user's generated site: the site in a frame with an English/Hindi switch, and an **Open your site in a new tab** link. It says plainly that putting the site live on the domain comes next, because hosting is not built yet. The only action left is **Start a new site**. If GoDaddy has not finished within about 30 seconds the run is `purchasing` and the screen offers **Check status**, which only checks and never buys again. A failed registration drops the used quote and the user gets a new one.
5. **Expiry and refresh.** The quote lasts about 10 minutes. A stale or expired quote is replaced when the screen opens, and **Get the current price** fetches a new one at any time.

**Demo mode** (`SHURU_DEMO_MODE`, default **on**). The quote is still real and free, but `POST /registrations` is never called, so nothing is registered or charged. The Buy screen and the confirmation say so ("Demo mode: no domain will be registered and nothing will be charged", "(not charged)"), the button reads **Complete demo purchase**, and the recorded purchase is marked as a demo. Real purchases need an explicit `SHURU_DEMO_MODE=false`. Because there are no user accounts yet, anyone holding a run's link can complete a real purchase, so demo mode stays on until accounts or the Approve gate exist. Demo mode needs a payment method and registrant contact on the GoDaddy account, because the quote checks them.

### Step 4: Confirm and launch

The only step that spends money or changes external state. In order:

1. **Approval gate (gate 2).** Show domain, price, hosting and what will happen. Nothing runs until Approve.
2. **Fresh quote.** `POST /registration-quotes` right before purchase. Re-quote if the token is older than about 8 minutes or reported expired.
3. **Agreements and contacts.** Show the agreements returned with the quote, require acceptance, fill registrant contacts from the operator's template.
4. **Purchase.** `POST /registrations` with the `quoteToken` and accepted agreements; it returns 202, so poll the registration until `COMPLETED` or `FAILED`.
5. **Package.** Wrap the HTML in a Node.js app and zip it (section 7).
6. **Host.** Using the `gddy` CLI (not in the v3 API): `gddy hosting app create`, `source upload`, `subscription attach`, `deployment publish`, polling each until done or timeout.
7. **DNS.** Create or replace records via `/zones/{zone}/dns-records`, listing existing records first. Do not wait for full propagation; show a note if the URL is not live yet.
8. **Result.** Show the live URL and the launch kit.

### Launch kit

- After launch, Claude (Haiku) returns 5 social posts, a welcome email (subject and body) and a 30-day checklist by week.
- Copyable in the UI. First feature cut if time runs short.

### Contact form

- A **Support** link in the header (right of the logo; icon only on narrow screens) opens a modal with the form and the line "Hi, need help? We reply within 1-2 days." The modal closes on the X, Esc or a backdrop click, traps focus, returns focus to the link, locks page scroll, and is full-screen under 600px. Wizard state is untouched. After a send it shows the thank-you with **Close** and **Send another message**. Fields: name (1 to 100 characters), email, message (1 to 5000 characters). Send is disabled until all three are filled.
- `POST /api/contact` validates the input, then sends one email from the Shuru mailbox to the Shuru mailbox with the visitor's address in `Reply-To`. The From address is never the visitor's, because the SMTP server would reject or spam-flag it.
- Abuse protection: a hidden honeypot field (filled means a bot; the server answers success and sends nothing), a per-client limit of 5 messages per hour (429 with a plain message), and rejection of line breaks in name and email (header injection).
- On success the user sees a thank-you. On failure they see a plain message and keep what they typed. If SMTP is not configured the endpoint returns 503 and the log says which variables are missing.

### Navigation and screen design

- **Stepper.** A header stepper shows Idea, Domain, Price, Site and Buy (and Launch, once hosting is built) as done, current or upcoming. Finished steps that are still open are clickable. Locked or not-yet-reached steps are disabled and say why ("Choose a domain first", "Locked once your site is written. Start over to change it"). On phones it shows "Step N of 5" and the current label only.
- **Logo.** Clicking the Shuru logo goes to the homepage, where a fresh run starts. If there is progress, a confirmation explains that the current site stays saved and can be reopened with the browser Back button or its link.
- **Resume.** The run and step are in the URL (`#/run/{id}/{step}`). Refresh, a pasted link and the browser Back button reopen the right step.
- **Locked after generation.** Once the site is generated, the domain cannot be changed. Domain and Price are locked; Idea (read-only), Site and Buy stay open. The Site screen offers **Buy domain** and **Start over**.
- **Locked after purchase.** Once the domain purchase has started (`purchasing`) or finished (`purchased`), every step before Buy is locked, including Idea and Site, and the stepper says why ("Locked once your domain is bought. Start over to make a new site."). Only Buy stays open, and **Start a new site** is the only action. A URL for a locked step is replaced by Buy. The backend enforces the same rule.
- **Homepage** (`#/`, shown whenever there is no run in the URL; no stepper): a hero with the headline "Turn one sentence into your own website", a short line on what Shuru does, and the idea form itself, so a visitor can start typing straight away. Beside it (below it on phones) a real sample: the example idea, then the site Shuru makes from it in a browser-style frame at `lucknowachaar.com`, with an English/Hindi switch. The sample pages are static files in `frontend/public/samples/`, rendered once through the real site template by `backend/scripts/render_samples.py` (hand-written content, no Claude call), so the homepage makes no API calls. Below the hero: "How it works" (four steps), three promises (nothing is bought without you, prices up front, native English and Hindi), a closing "Start my site" button that moves focus to the idea box, and a footer with a Support link. The copy promises a domain and a website preview, not a live URL, until hosting is built. Entrance animations are turned off for users who prefer reduced motion.
- **Idea form** (in the homepage hero): a 0 to 500 character counter, clickable example ideas and an English/Hindi switch. There is no separate summary screen: after "Create my business summary" the user goes straight to the Domain step, which shows the summary (tagline, name ideas, folded audience and tone) while it searches for domains. Going back to the Idea step later shows a read-only "Your idea" card (the idea text, the language and the same summary) with a button back to wherever the run is ("Back to domains", "Back to the price" or "Back to your site"). The idea cannot be edited, because the summary and domains were made from it; **Start over** makes a new one.
- **Domain screen** (headed "Choose your domain"): a compact business reminder at the top (tagline, the name ideas as tappable chips, and audience and tone folded away under "More about your business"). Tapping a name idea searches for it; tapping it again returns to the default suggestions. Then a "Looking for something else?" search, domain cards with first-year and renewal price (and, for a premium domain, a line such as "Premium domain: plus a one-time fee of $3,900.00"), loading skeletons, a "Try again" button on errors, and the note that prices exclude taxes and fees.
- **Price screen** (step id `review`, headed "Check the price"): the price shown prominently, a premium-domain fee line and a "Total first year" (price plus fees, before ICANN fees and taxes) when there is a fee, the "Nothing is purchased yet" note, a primary Confirm button and a secondary "Pick a different domain" button, and a progress panel while the site is written (about 20 seconds).
- **Site screen** (step id `preview`, headed "Preview your site"): a language switch, a preview that fits the window, "Regenerate (N of 3 left)", and a "What's next" panel with **Buy domain** (opens the Buy step) and **Start over**.
- **Buy screen:** see "Step 4a". The price and domain in a summary box, the agreement links with an "I have read and agree" tick, a clear demo-mode notice when it applies, **Complete demo purchase** or **Buy domain**, **Get the current price** and **Back to preview**. Afterwards a confirmation with the site shown in a frame and a link to open it (or a pending screen with **Check status**).
- **Brand and colour.** The logo is a green tile with a "start" arrow, the wordmark "Shuru" with a turmeric dot, and "शुरू" (Hindi for "start"); the favicon uses the same mark. The palette is green plus one warm turmeric accent (`#E9A23B`) for small highlights such as the current-step ring and the tagline bar. Turmeric is never used for text on white (2.2:1 contrast); secondary text is at least 8:1 and placeholders about 5.8:1.
- **Accessibility:** focus moves to the new screen's heading on every step change, loading and errors are announced to screen readers, the page title follows the step, and Hindi text carries `lang="hi"`.
- Out of scope for now: dark mode, a "test environment" badge, and "continue your last site" from browser storage (section 17).

### Runs and replay (replay planned)

- Each run saves its brief, domains, site JSON, purchase, hosting and DNS results, live URL and launch kit.
- **Replay mode** opens a saved, successful run and steps through it in the same UI. The responses come from stored fixtures instead of Claude and GoDaddy, so it makes no external calls, spends no credits and buys nothing. Uses: the demo fallback if the network or an API fails on stage, UI work without spending credits, and repeatable tests. Replayed runs are clearly labelled "Replay", and their Approve button cannot buy anything.
- Data files (`data/`, `*.sqlite`) are git-ignored.

## 6. Claude integration

| Call | Step | Model | Output |
| --- | --- | --- | --- |
| 1. Brief + name safety | 1 | Haiku 5.5 | Brief JSON with per-name flags |
| Domain scout agent (tool use) | 2 | Haiku 5.5 | 5 chosen domains with reasons, plus a trace |
| 2. Site | 3 | Sonnet 5.5 | Site JSON |
| 3. Launch kit | After 4 | Haiku 5.5 | Launch kit JSON |

- Every call sets `max_tokens` (values set after Day 1 measurement).
- Use prompt caching for the system prompt and site schema.
- Send only the fields each call needs.
- Validate output with Pydantic; one retry, then a recoverable error.
- Log tokens and estimated cost per call and per run.
- Model IDs are config values, not hard-coded.
- Claude never decides anything about purchases, DNS or hosting, and only the scout agent has tools (read-only).

## 7. Hosting package

GoDaddy Hosting runs Node.js apps. Each site is wrapped as a small app that has:

- `package.json` with non-empty `name` and `version`
- `build` and `start` scripts
- a server listening on the `PORT` environment variable (Node's built-in `http`, no dependencies)
- no `node_modules` folder in the zip

Packaging has its own tests and must not call GoDaddy.

## 8. Non-functional requirements

- **Safety (hard invariant):** no purchase, hosting write or DNS write runs without explicit approval for that run. Today the purchase needs a stored, unexpired quote and matching accepted agreements and price (server-side), and never calls `POST /registrations` while `SHURU_DEMO_MODE` is on. Covered by tests. The separate Approve gate is added with hosting.
- **Test money:** use the `ote` environment where possible and `--dry-run` for DNS. Buy only one cheap domain for rehearsal.
- **Secrets:** the GoDaddy PAT, Anthropic key and the mailbox SMTP password come from environment variables, never reach the frontend, logs, git or the Docker image.
- **Abuse and spend:** per-client limits on run creation (10 per hour, built) and contact messages (5 per hour, built), a regeneration cap per run, and a monthly spend limit in the Anthropic Console.
- **Prompt injection:** see section 8a.
- **Timeouts:** every external call has one; polling has an overall deadline.
- **Recovery:** each run has a state. Built: `briefed`, `domains_listed`, `domain_chosen`, `site_generated`, `purchasing`, `purchased`. Planned: `approved`, `published`, `dns_connected`, `kit_generated`, `complete`, plus `failed` from any state (architecture section 5 is the reference). If a step fails after purchase, the run keeps its state so the user can resume without buying twice. A purchase is never retried silently: a repeat call only checks on a pending purchase, and a retry after a timeout reuses the quote's idempotency key so the domain is not bought twice.
- **Logging:** one line per step with command, exit code, token counts and timestamps.
- **Performance:** brief and site each under 30 seconds; checking 5 domains under 15 seconds.
- **Language and access:** Hindi (Devanagari) text, keyboard navigation, correct `lang` attributes on the generated site and on Hindi text in the wizard, visible focus, focus moved to each new screen, and a layout that works on phones.
- **Cost:** about $40 building, $10 testing, $5 rehearsals, $45 reserve. Use fixtures for UI work.

## 8a. Prompt-injection safeguards

Founders' text (the idea, keywords) goes into Claude prompts, and Claude's output goes into a public website. Defences, in layers:

1. **Input rules.** Length limits (500-character idea, domain-label keywords) and a plain-text-only idea.
2. **Data, not instructions.** User text is wrapped in delimiters (`<idea>…</idea>`), and the system prompt says to treat it only as a description of a business and never as instructions. Any `<idea>`/`<brief>` tags inside the text are removed, so a visitor cannot close the tag early (built, `services/prompts.py`).
3. **Structured output only.** Every reply must match a Pydantic schema with length limits, so injected "say X" text has nowhere to go except normal fields. Invalid output gets one retry, then an error.
4. **Output checks (built).** Every text field in the brief and site is checked before it is saved or shown. It must not contain links or domains (the run's own domain is allowed), email addresses, phone numbers (9 or more digits, including Devanagari digits), HTML, script or template code, or prompt-like phrases ("ignore previous instructions", "system prompt", "as an AI"). A reply that breaks a rule gets one retry, with the broken fields named; a second failure shows "Try again". The prompt already forbids inventing contact details, so normal replies pass.
5. **The template owns HTML.** Content is HTML-escaped (Jinja autoescape), and the preview iframe is sandboxed, so injected markup cannot run.
6. **Least privilege for agents.** The scout's tools are read-only and validated (domain patterns, a call cap). Even a successful injection cannot buy, publish or change DNS, because those actions are not tools and need Approve.
7. **No secrets in prompts.** Prompts never contain keys, tokens, contact details or other users' data, so there is nothing to leak.
8. **Logging and tests.** A set of known injection ideas is kept as test fixtures, and the outputs are checked against rules 3 to 5.

## 9. Architecture

```
React wizard (Vite): idea, domain, review, preview, confirm
   |
FastAPI backend (orchestrator owns the sequence; rate limits on runs and contact)
   |-- Claude: brief + name safety (Haiku)
   |-- Claude domain scout agent (Haiku, tool use) --> read-only tools: GoDaddy suggest / check availability
   |-- [gate 1: user confirms cost]
   |-- Claude: site JSON (Sonnet) -> HTML template
   |-- [gate 2: Approve]
   |-- GoDaddy REST: quote -> purchase
   |-- package Node.js app -> gddy hosting upload / publish
   |-- GoDaddy REST: DNS records
   |-- Claude: launch kit (Haiku)
   |-- SQLite: runs and replay fixtures
```

| Layer | Choice |
| --- | --- |
| Frontend | React with Vite |
| Backend | Python with FastAPI |
| Claude | Anthropic Python SDK with Pydantic validation; tool use for the scout agent |
| GoDaddy | v3 REST API (`httpx`); `gddy` CLI only for hosting, later |
| Storage | SQLite |
| Dev | GitHub Codespaces with Claude Code |
| App hosting | GoDaddy Gen4 Linux VPS, Docker Compose (backend + Caddy), Ubuntu 24.04, shuru.biz (decided); `gddy` is installed in the backend image once the hosting step is built |

Backend layout: `core/` (settings, errors, logging), `models/` (what we store), `schemas/` (request bodies and GoDaddy's raw JSON), `routes/`, `services/` (Claude, domains, site, mail, orchestrator), `clients/` (GoDaddy), `repositories/` (SQLite run store) and `utils/`. The frontend groups `components/` into `steps/`, `dialogs/`, `forms/` and `ui/`, with `lib/`, `hooks/`, `utils/` and `styles/` beside them. Details are in `architecture.md` section 12.

## 10. Error handling

| Error | Behaviour |
| --- | --- |
| Claude output invalid | One retry, then "Try again" |
| No available domains | "Try different names" |
| Quote expired | Fetch a fresh quote and show the new price (the Buy screen does this on opening; the purchase is refused if the lock has passed) |
| Domain taken at quote or purchase | "Sorry, that domain was just taken" |
| Accepted price or agreements do not match the quote | Refuse (409) and ask the user to review again |
| Quote fails (no payment method or contact on the account) | Plain "couldn't reach the domain service" message; the reason is in the logs |
| Registration still pending after about 30 seconds | Run becomes `purchasing`; **Check status** polls without buying again |
| Registration fails | Show error, drop the used quote, allow a new quote and retry |
| Purchase fails before charge | Show error, keep run, allow retry |
| Purchase succeeds, hosting fails | Keep run as `purchased`, show domain as owned, offer to retry hosting, never buy again |
| Publish times out | Poll to deadline, show status, offer retry |
| DNS not propagated | Show live URL with a propagation note |
| Network failure in demo | Switch to replay mode |
| Too many runs from one client | 429 with "You've started a few sites already. Please try again in a little while." |
| Scout agent hits its step cap, budget or deadline | Return the options found so far; if there are none, fall back to the fixed search |
| Idea or name fails the safety check | Polite stop, or a warning on the name; no domain or site calls for a blocked idea |
| Contact mail cannot be sent (SMTP login rejected, timeout) | "We couldn't send your message"; the log has the server reply. First check the host is `smtpout.secureserver.net` and the username is the full address |

Users see plain-language messages. Raw API and CLI output goes to logs only.

## 11. Risks and fallbacks

| Risk | Fallback |
| --- | --- |
| Purchase API unavailable for the account | Stop at the locked quote; use a pre-registered domain for DNS and publish |
| Tests buy real domains | Use the test environment, list DNS records before writing, one cheap rehearsal domain |
| No hosting plan or Node.js upload fails | Deploy to a free static host (Cloudflare Pages, Netlify, Vercel) and point GoDaddy DNS at it |
| `gddy` cannot install on the backend host (hosting step only) | Use the static-host fallback, or run publish from the Codespace |
| Slow DNS propagation | Pre-warm a domain already owned; show the rehearsal URL |
| Credits run low | Replay fixtures, Haiku everywhere except the site call |
| Scope creep | Cut launch kit first, then Hindi toggle. Never cut the domain-to-live-URL path |
| Network failure in demo | Recorded backup video and replay mode |
| Prompt injection through the idea text | Section 8a: delimiters, schema-only output, escaped template, read-only agent tools |
| Agent loops or overspends | Step cap, token budget, deadline; the trace is logged per run |
| Public site burns Claude credits | Per-client run limit (built), Anthropic Console spend limit |

## 12. Scope and plan

**Must have:** steps 1 to 4 with both approval gates, domain search and quote, purchase (built, demo mode by default), package and publish, DNS, live URL, replay, rate limit on run creation (done).
**Should have:** domain scout agent with a visible trace, name safety check, prompt-injection safeguards (section 8a), Hindi and English toggle, launch kit.
**Later:** section 17.

| Day | Focus | Exit criteria |
| --- | --- | --- |
| 1 | Payment method, PAT, practise against the test environment; FastAPI and React skeletons; Claude call 1 | Brief shows in UI; GoDaddy REST calls work; hosting plan and host install verified |
| 2 | GoDaddy REST client, domain picker, cost review, quote and purchase behind Approve | Approve gate tested; purchase works in `ote` or on one rehearsal domain. Built: quote and purchase with demo mode; still to do: one real rehearsal purchase |
| 3 | Template, Claude call 2, preview, language toggle, packaging | Zip passes section 7 checks; preview renders from real generation |
| 4 | Upload, attach, publish with polling; DNS; confirm screen; launch kit | Live URL opens from a real run; run saved; replay works |
| 5 | Error states, backup video, README, slide, 3 to 4 rehearsals | Rehearsals take about 10 minutes |

## 13. Demo script (about 4 minutes)

1. **Problem (20s):** launching online takes a week and five tools.
2. **Input (20s):** type the achaar-in-Lucknow sentence.
3. **Brief and names (40s):** brief appears; the scout agent's trace shows it trying, rejecting and refining names, then domains with prices. Point out that it only proposes.
4. **Preview (40s):** a real site appears; switch to Hindi.
5. **Approval (20s):** two gates: the user confirmed the cost before the site was written, and nothing is bought until Approve. Agentic legwork, human decisions.
6. **Go live (40s):** purchase, publish, DNS, open the real URL.
7. **Launch kit (20s):** social posts and 30-day checklist.
8. **Impact (20s):** idea to live business in 10 minutes; next: payments and email.

The live registration uses a domain bought during rehearsal. If it fails, switch to the cached run and say so.

## 14. Success metrics

- An end-to-end run from idea to live URL in about 10 minutes.
- Zero purchases without a recorded approval (tests and logs), and zero registrations while demo mode is on.
- At least 3 of 4 rehearsals complete unaided, each with a replay fallback.
- Build spend within the credit plan.
- Generated site passes packaging checks and renders in English and Hindi.
- The scout agent finds at least 5 available domains within its step cap in 4 of 5 test ideas.
- No known injection fixture changes the generated site beyond normal content (section 8a).
- GoDaddy capabilities used end to end: domain suggest, availability, quote, purchase, DNS, hosting.

## 15. Dependencies and glossary

**Dependencies:** GoDaddy account with payment method and PAT; GoDaddy VPS with Docker; `gddy` in the backend image (hosting step only); Anthropic API key with a spend limit; Node.js on the hosting target; GoDaddy's "Connect your domain" hosting guide (read on Day 1).

**Glossary:** `gddy` is GoDaddy's CLI, used here for hosting only. `ote` is the GoDaddy test environment (`prod` is real). A PAT is a Personal Access Token used instead of browser OAuth. A quote token is a roughly 10-minute price lock. Replay mode shows a saved run with no external calls. A gate is a manual approval step that the flow cannot pass without the user. The scout agent is a Claude tool-use loop with read-only tools.

## 16. Sources

- [Set up the CLI](https://developer.godaddy.com/en/docs/api-users/cli/set-up)
- [CLI workflow reference](https://developer.godaddy.com/en/docs/api-users/cli/reference)
- [Node.js app requirements](https://developer.godaddy.com/en/docs/api-users/hosting/app-requirements)

## 17. Future improvements

Not in the current plan; candidates once the must-haves ship.

**Help customers reach and pay the business**

- WhatsApp click-to-chat button (`wa.me/<number>`) on generated sites, with the number entered by the owner.
- UPI payment link or QR code on the site.
- A simple contact form on generated sites, delivered to the owner's email.
- A WhatsApp Business catalog from the site's offer items.

**Get found**

- Meta tags, Open Graph preview card (for links shared on WhatsApp), `sitemap.xml`, `robots.txt` and `LocalBusiness` structured data in the template.
- A Google Business Profile setup checklist in the launch kit.

**Inclusion and reach**

- Voice input for the idea (browser Web Speech API, `hi-IN` and `en-IN`) for founders who would rather speak than type.
- More Indian languages generated natively (Tamil, Bengali, Marathi, Telugu); mostly prompt and schema work.

**Manage after launch**

- Edit the site with a sentence ("make it festive for Diwali", "add mango pickle"): Claude edits the site JSON, the template keeps the layout, and the user previews before publishing.
- Post-launch check-up agent (read-only tools): checks that DNS resolves, the site loads over HTTPS and the page renders, then produces the launch kit and a first-week to-do list.
- A professional email address (`hello@yourdomain`) through GoDaddy email forwarding or Titan, offered in "What's next".
- Logo concept for the brand.

**Platform**

- SSE progress updates instead of polling.
- A shared rate limiter (for example Redis) if Shuru runs more than one backend process, and a global daily cap on runs.
- Dark mode, a "test environment" badge, and "continue your last site" from browser storage.

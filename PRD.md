# LaunchPad: Product Requirements Document

| | |
| --- | --- |
| **Status** | Draft v0.2 |
| **Scope** | Hackathon MVP, solo build, 5 days, $100 in Claude credits |
| **Stack** | Python (FastAPI), React (Vite), Anthropic Python SDK, `gddy` GoDaddy CLI |
| **Source** | `LaunchPad Simplified Build Plan.md` |

## 1. Summary

LaunchPad turns one sentence into a live website on a domain the user owns, in about 10 minutes. A first-time founder types an idea (e.g. "I make homemade achaar in Lucknow and want to sell online"), picks English or Hindi, chooses a domain, previews a generated one-page site, approves the purchase, and gets a live URL and a launch kit.

It is a **guided 4-step wizard, not an agent**. Application code controls the sequence. Claude only generates structured JSON at fixed points. The `gddy` CLI handles domains, DNS and hosting.

**Problem:** first-time founders stall between "I have an idea" and "I have a URL". Too many decisions (name, domain, site, copy) and too many tools.

**Pitch:** "Idea to live business in 10 minutes, with AI doing the thinking and GoDaddy making it real."

## 2. Goals and non-goals

**Goals**

- Go from one sentence to a live site on an owned domain, end to end.
- Never spend money without explicit user approval.
- Produce a consistent, polished site from Claude JSON filling a fixed template.
- Support English and Hindi.
- Keep Claude cost low: one call per step, capped tokens, Haiku where possible.
- Keep the flow deterministic, testable and replayable.

**Non-goals**

- Autonomous agent behaviour.
- Renewals, forwarding, registry lock, contact updates.
- Site editing, CMS, e-commerce, email hosting, logo or SEO tools.
- User accounts, end-user billing, production auth.

## 3. Decisions and assumptions

These replace the earlier open questions. Change any that are wrong.

- **Single operator.** The demo uses the developer's GoDaddy account, payment method and registrant contact details. No end-user accounts.
- **One static page** rendered from one template.
- **Hindi and English** are both **generated natively** by Claude in the single site call, from the same structured brief. Hindi is not translated from the English text, because native output reads more naturally. Facts (prices, places, contact details) must match across languages, and a native speaker spot-checks samples. The toggle costs nothing extra.
- **Models:** Haiku 5.5 for the brief and launch kit, Sonnet 5.5 for the site. No separate ranking call; domain availability decides.
- **Regeneration cap:** 3 per run.
- **Agreements:** ICANN agreement text is shown in the UI and must be accepted.
- **Storage:** **SQLite** (decided; no JSON-file store). If the host disk is ephemeral, replay fixtures are committed to the repo.
- **Progress updates:** **polling** (decided). The frontend calls `GET /runs/{id}` about every 2 seconds until the run is `live` or `failed`. SSE is a possible later upgrade, not part of this build.
- **Hosting for Shuru itself:** Node.js or a VPS, to be chosen later. Details to be explored later.
- **GoDaddy hosting plan:** the account has one, so GoDaddy Hosting is the default publishing target and the static-host fallback is only for failures.
- **Approval** is the Approve click on step 4, with no separate authentication.
- **Template** is neutral; no brand styling required.

Still to verify on Day 1: the hosting plan supports Node.js, and the backend host can install `gddy` (see section 9).

## 4. User flow

| # | Step | User does | System does |
| --- | --- | --- | --- |
| 1 | Describe idea | Types a sentence, picks language | Claude call 1: brief and name ideas |
| 2 | Pick domain | Chooses from available domains with prices | `gddy` suggest and availability |
| 3 | Preview site | Reads site, toggles language, may regenerate | Claude call 2: site JSON rendered in template |
| 4 | Confirm and launch | Reviews domain, price, preview; clicks **Approve** | Quote, purchase, package, publish, DNS, then Claude call 3: launch kit |

## 5. Functional requirements

### Step 1: Idea and brief

- Input is 1 to 500 characters plus `en` or `hi`. Empty input is rejected by UI and API.
- Claude (Haiku) returns a JSON brief: `audience`, `tone`, `tagline`, and 8 to 10 `name_ideas`.
- The brief is validated with Pydantic. On failure, retry once, then show a "Try again" error.
- The brief is shown to the user before the domain step.

### Step 2: Domains

- Run `gddy domain suggest` (`--tlds com,net,io --limit 5`) using the brief's names. Merge and de-duplicate.
- Check each candidate with `gddy domain available`, in parallel with timeouts. Use `--check-type full` only on the final pick.
- Show only available domains with prices. If none, offer "Try different names" with the user's own keyword.
- No Claude call in this step.
- All `gddy` calls go through one wrapper module that parses JSON.

### Step 3: Site and preview

- Claude (Sonnet) returns site JSON: `hero`, `offer`, `about`, `faq` (3 to 5 items), `contact` (display fields only), with English and Hindi text, each generated natively (not translated).
- Validate with Pydantic. Retry once on failure.
- One HTML template renders the JSON and is the only source of layout and style.
- Live preview in the wizard, language toggle, regenerate (capped).

### Step 4: Confirm and launch

The only step that spends money or changes external state. In order:

1. **Approval gate.** Show domain, price, hosting and what will happen. Nothing runs until Approve.
2. **Fresh quote.** `gddy domain quote` right before purchase. Re-quote if the token is older than about 8 minutes or reported expired.
3. **Agreements and contacts.** Show `gddy domain agreements`, require acceptance, fill registrant contacts from the operator's template.
4. **Purchase.** `gddy domain purchase --quote-token <token> --agree --confirm`.
5. **Package.** Wrap the HTML in a Node.js app and zip it (section 7).
6. **Host.** `gddy hosting app create`, `source upload`, `subscription attach`, `deployment publish`, polling each until done or timeout.
7. **DNS.** `gddy dns add` or `set`, previewed with `--dry-run` first. Do not wait for full propagation; show a note if the URL is not live yet.
8. **Result.** Show the live URL and the launch kit.

### Launch kit

- After launch, Claude (Haiku) returns 5 social posts, a welcome email (subject and body) and a 30-day checklist by week.
- Copyable in the UI. First feature cut if time runs short.

### Runs and replay

- Each run saves its brief, domains, site JSON, purchase, hosting and DNS results, live URL and launch kit.
- Replay mode shows a saved run through the same UI with no external calls. It is the fallback for network failure.
- Data files (`data/`, `*.sqlite`) are git-ignored.

## 6. Claude integration

| Call | Step | Model | Output |
| --- | --- | --- | --- |
| 1. Brief | 1 | Haiku 5.5 | Brief JSON |
| 2. Site | 3 | Sonnet 5.5 | Site JSON |
| 3. Launch kit | After 4 | Haiku 5.5 | Launch kit JSON |

- Every call sets `max_tokens` (values set after Day 1 measurement).
- Use prompt caching for the system prompt and site schema.
- Send only the fields each call needs.
- Validate output with Pydantic; one retry, then a recoverable error.
- Log tokens and estimated cost per call and per run.
- Model IDs are config values, not hard-coded.
- Claude never decides anything about purchases, DNS or hosting.

## 7. Hosting package

GoDaddy Hosting runs Node.js apps. Each site is wrapped as a small app that has:

- `package.json` with non-empty `name` and `version`
- `build` and `start` scripts
- a server listening on the `PORT` environment variable (Node's built-in `http`, no dependencies)
- no `node_modules` folder in the zip

Packaging has its own tests and must not call GoDaddy.

## 8. Non-functional requirements

- **Safety (hard invariant):** no purchase, hosting write or DNS write runs without Approve for that run. Covered by tests.
- **Test money:** use the `ote` environment where possible and `--dry-run` for DNS. Buy only one cheap domain for rehearsal.
- **Secrets:** the GoDaddy PAT and Anthropic key come from environment variables, never reach the frontend, logs or git.
- **Timeouts:** every external call has one; polling has an overall deadline.
- **Recovery:** each run has a state (`brief`, `domain_selected`, `site_ready`, `approved`, `purchased`, `hosted`, `dns_set`, `live`, `failed`). If a step fails after purchase, the run keeps its state so the user can resume without buying twice. A purchase is never retried silently.
- **Logging:** one line per step with command, exit code, token counts and timestamps.
- **Performance:** brief and site each under 30 seconds; checking 5 domains under 15 seconds.
- **Language and access:** Hindi (Devanagari) text, keyboard navigation, correct `lang` attributes on the generated site.
- **Cost:** about $40 building, $10 testing, $5 rehearsals, $45 reserve. Use fixtures for UI work.

## 9. Architecture

```
React wizard (Vite): idea, domain, preview, confirm
   |
FastAPI backend
   |-- Claude: brief (Haiku)
   |-- gddy: domain suggest / available
   |-- Claude: site JSON (Sonnet) -> HTML template
   |-- gddy: quote -> purchase           (only after Approve)
   |-- package Node.js app -> gddy hosting upload / publish
   |-- gddy: DNS records
   |-- Claude: launch kit (Haiku)
   |-- SQLite: runs and replay fixtures
```

| Layer | Choice |
| --- | --- |
| Frontend | React with Vite |
| Backend | Python with FastAPI |
| Claude | Anthropic Python SDK with Pydantic validation |
| GoDaddy | `gddy` CLI (REST API as fallback) |
| Storage | SQLite |
| Dev | GitHub Codespaces with Claude Code |
| App hosting | Render or Railway; must be able to install `gddy` at build time |

Suggested backend modules: `api/`, `claude/`, `godaddy/`, `site/`, `runs/`, `replay/`.

## 10. Error handling

| Error | Behaviour |
| --- | --- |
| Claude output invalid | One retry, then "Try again" |
| No available domains | "Try different names" |
| Quote expired | Fetch a fresh quote and show the new price |
| Purchase fails before charge | Show error, keep run, allow retry |
| Purchase succeeds, hosting fails | Keep run as `purchased`, show domain as owned, offer to retry hosting, never buy again |
| Publish times out | Poll to deadline, show status, offer retry |
| DNS not propagated | Show live URL with a propagation note |
| Network failure in demo | Switch to replay mode |

Users see plain-language messages. Raw CLI output goes to logs only.

## 11. Risks and fallbacks

| Risk | Fallback |
| --- | --- |
| Purchase API unavailable for the account | Stop at the locked quote; use a pre-registered domain for DNS and publish |
| Tests buy real domains | Use `ote`, `--dry-run`, one cheap rehearsal domain |
| No hosting plan or Node.js upload fails | Deploy to a free static host (Cloudflare Pages, Netlify, Vercel) and point GoDaddy DNS at it |
| `gddy` cannot install on the backend host | Use the GoDaddy REST API, or run purchase and publish from the Codespace |
| Slow DNS propagation | Pre-warm a domain already owned; show the rehearsal URL |
| Credits run low | Replay fixtures, Haiku everywhere except the site call |
| Scope creep | Cut launch kit first, then Hindi toggle. Never cut the domain-to-live-URL path |
| Network failure in demo | Recorded backup video and replay mode |

## 12. Scope and plan

**Must have:** steps 1 to 4 with the approval gate, domain search and quote, purchase, package and publish, DNS, live URL, replay.
**Should have:** Hindi and English toggle, launch kit.
**Could have:** logo concept, SEO checklist, WhatsApp catalog.

| Day | Focus | Exit criteria |
| --- | --- | --- |
| 1 | Install `gddy`, payment method, PAT, practise on `ote`; FastAPI and React skeletons; Claude call 1 | Brief shows in UI; `gddy` works in `ote`; hosting plan and host install verified |
| 2 | `gddy` domain wrapper, domain picker, quote and purchase behind Approve | Approve gate tested; purchase works in `ote` or on one rehearsal domain |
| 3 | Template, Claude call 2, preview, language toggle, packaging | Zip passes section 7 checks; preview renders from real generation |
| 4 | Upload, attach, publish with polling; DNS; confirm screen; launch kit | Live URL opens from a real run; run saved; replay works |
| 5 | Error states, backup video, README, slide, 3 to 4 rehearsals | Rehearsals take about 10 minutes |

## 13. Demo script (about 4 minutes)

1. **Problem (20s):** launching online takes a week and five tools.
2. **Input (20s):** type the achaar-in-Lucknow sentence.
3. **Brief and names (40s):** brief appears, then domains with prices.
4. **Preview (40s):** a real site appears; switch to Hindi.
5. **Approval (20s):** nothing is bought until Approve.
6. **Go live (40s):** purchase, publish, DNS, open the real URL.
7. **Launch kit (20s):** social posts and 30-day checklist.
8. **Impact (20s):** idea to live business in 10 minutes; next: payments and email.

The live registration uses a domain bought during rehearsal. If it fails, switch to the cached run and say so.

## 14. Success metrics

- An end-to-end run from idea to live URL in about 10 minutes.
- Zero purchases without a recorded Approve (tests and logs).
- At least 3 of 4 rehearsals complete unaided, each with a replay fallback.
- Build spend within the credit plan.
- Generated site passes packaging checks and renders in English and Hindi.

## 15. Dependencies and glossary

**Dependencies:** GoDaddy account with payment method and PAT; `gddy` on the Codespace and backend host; Anthropic API key with a spend limit; Node.js on the hosting target; GoDaddy's "Connect your domain" hosting guide (read on Day 1).

**Glossary:** `gddy` is GoDaddy's CLI. `ote` is its test environment (`prod` is real). A PAT is a Personal Access Token used instead of browser OAuth. A quote token is a roughly 10-minute price lock. Replay mode shows a saved run with no external calls.

## 16. Sources

- [Set up the CLI](https://developer.godaddy.com/en/docs/api-users/cli/set-up)
- [CLI workflow reference](https://developer.godaddy.com/en/docs/api-users/cli/reference)
- [Node.js app requirements](https://developer.godaddy.com/en/docs/api-users/hosting/app-requirements)

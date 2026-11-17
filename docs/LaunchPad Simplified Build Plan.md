# LaunchPad: Simplified Build Plan

*From one sentence to a live website on your own domain, powered by Claude and GoDaddy. Built with Python (FastAPI) + React. Solo, 5 days, $100 in Claude credits.*

## Why simplify

The judges said the solution does not have to be agentic. That lets us replace the autonomous agent with a **guided wizard** where Claude does the smart parts at fixed steps. The idea is unchanged (one sentence to a live site on your own domain), but the build is simpler, cheaper and safer for a solo, 5-day challenge.

## What changes

|  | Agent version | Simplified version |
| --- | --- | --- |
| Control flow | Claude decides which tool to call next | Your code runs a fixed sequence of steps |
| Claude's role | Orchestrator plus generator | Generator only, with 3 focused calls returning JSON |
| UI | Live agent timeline | 4-step wizard with progress bar |
| Approval gate | Special agent rule | A natural "Confirm and buy" step |
| Debugging | Unpredictable loops | Deterministic and easy to test |
| Credit use | Higher, since agent loops re-send context | Much lower, one call per step |

## The idea

An entrepreneur types one sentence, for example "I make homemade achaar in Lucknow and want to sell online". LaunchPad sharpens the idea, finds and prices a domain, builds the website, asks the user to approve the purchase, registers the domain, connects DNS, publishes the site and hands over a launch kit.

**Why it is a real problem:** first-time founders stall between "I have an idea" and "I have a URL". They face too many decisions (name, domain, site, copy) and too many tools. LaunchPad compresses that into about 10 minutes and one guided flow.

**What makes it stand out:**

- A real end-to-end result: a live URL on a domain the user owns.
- Human approval before any money is spent.
- Hindi and English output, which suits small Indian businesses and creators.
- Claude returns structured JSON that fills a polished fixed template, so the design stays consistent.

## What GoDaddy provides

GoDaddy now ships a CLI called `gddy` that covers the whole path from domain search to a live hosted app, so LaunchPad can drive GoDaddy without hand-written API plumbing.

| Step | Command | Notes |
| --- | --- | --- |
| Suggest names | `gddy domain suggest "<query>" --tlds com,net,io --limit 5` | Takes a keyword or phrase |
| Check a name | `gddy domain available <domain>` | `--check-type full` is slower but definitive |
| Lock a price | `gddy domain quote <domain>` | Returns a quote token, valid for about 10 minutes |
| Required agreements | `gddy domain agreements --tld <tld>` | ICANN agreements for the registration |
| Buy | `gddy domain purchase --quote-token <token> --agree --confirm` | Charges the account; needs registrant contacts (`gddy domain contacts init` writes a template) |
| DNS | `gddy dns list`, `add`, `set`, `delete` | `add` appends, `set` replaces every record of a type and name; `--dry-run` previews |
| Hosting | `gddy hosting app create`, `source upload`, `subscription attach`, `deployment publish` | Node.js apps only; poll each operation until it completes |

**How the CLI behaves:**

- **Login:** the first command opens a browser for OAuth, which a server cannot do. The backend uses a Personal Access Token instead, stored with `gddy pat add` or passed in the `GDDY_PAT` environment variable. The CLI checks for a PAT before falling back to OAuth.
- **Environments:** `gddy env set ote` selects the test environment and `prod` the real one. `--env` overrides it for one command.
- **Output:** JSON by default when not in an interactive terminal, with `--fields`, `--filter` and `--schema` to shape or describe it. That makes it easy for FastAPI to parse.
- **Payment:** a payment method must be on the GoDaddy account before any purchase. `gddy payment-methods add` opens the page.
- **Discovery:** `gddy tree` prints every command in the installed version, and `gddy guide <topic>` gives built-in walkthroughs, such as `domain-purchase`.
- **Gaps:** renewals, domain forwarding, registry lock and contact updates are not in the CLI yet and need the REST API. None of them are needed for the demo.

**Two helpers for building:** an agent skill that lets Claude Code install and drive `gddy` for you, and a read-only GoDaddy MCP server for domain search without installing anything.

**Verify on Day 1:**

- The `ote` test environment works with your account and PAT.
- A payment method is on the account.
- Your account has a hosting plan (`gddy hosting subscription list` shows it).
- The backend host can install the `gddy` binary. The installer puts it in `~/.local/bin` and does not change your `PATH`.
- Read GoDaddy's "Connect your domain" hosting guide, which this plan has not covered yet.

**Hosting:** GoDaddy Hosting runs Node.js apps. The upload must be a zip with a `package.json` (non-empty name and version), a `build` script and a `start` script, an app that listens on the `PORT` environment variable, runtime packages under `dependencies`, and no `node_modules` folder. So each generated site is wrapped in a tiny Node server that serves the generated HTML, zipped, uploaded, attached to your hosting plan and published. If you have no hosting plan or the upload fails, the fallback is a free static host (Cloudflare Pages, Netlify or Vercel) with GoDaddy DNS pointing at it.

## The simplified flow

1. **Describe your idea.** The user types one sentence and picks English or Hindi.
2. **Claude call #1 (Haiku or Sonnet):** returns a JSON brief with audience, tone, tagline and 8 to 10 name ideas.
3. **Domain step (no AI cost):** the FastAPI backend asks GoDaddy for suggestions and checks availability with the CLI, then the React app shows a list with prices. The user picks one.
4. **Claude call #2 (Sonnet):** generates the one-page site as structured JSON (hero, offer, about, FAQ, contact) that your template renders, with a live preview.
5. **Confirm and launch:** the user reviews domain, price and preview, then clicks Approve. The backend gets a quote, purchases with the quote token, packages the site as a small Node.js app, uploads and publishes it on GoDaddy Hosting, and adds the DNS records.
6. **Claude call #3 (Haiku):** produces the launch kit with 5 social posts, a welcome email and a 30-day checklist.

## Architecture

```
React wizard (browser)
   |  4 steps: idea, domain, preview, confirm
   v
FastAPI backend
   |-- Claude API: brief (JSON)
   |-- gddy CLI: domain suggest / available
   |-- Claude API: site content (JSON) -> HTML template
   |-- gddy CLI: quote -> purchase (after Approve)
   |-- package site as Node.js app -> gddy hosting upload / publish
   |-- gddy CLI: DNS records
   |-- Claude API: launch kit (JSON)
```

**Model strategy:** Sonnet 5.5 for site generation, Haiku 5.5 for the brief, ranking and launch kit. Cap `max_tokens` on every call.

**Tech stack:**

| Layer | Choice | Role |
| --- | --- | --- |
| Frontend | React (built with Vite) | The 4-step wizard with live site preview |
| Backend | Python with FastAPI | One endpoint per step; runs the Claude calls and the `gddy` commands |
| Claude | Anthropic Python SDK | 3 calls returning JSON, checked with Pydantic models |
| GoDaddy | `gddy` CLI called from the backend | Domains, DNS and hosting; the REST API is the fallback |
| Storage | SQLite or a JSON file | Saves finished runs for demo replay |
| Dev environment | GitHub Codespaces with Claude Code | Everything stays in the browser |
| Hosting the app | A host that can run a build script, such as Render or Railway | Must be able to install the `gddy` binary at build time |

## Credit plan ($100)

Exact per-token prices should be checked on the pricing page and Console usage dashboard on Day 1, then recalibrated.

| Bucket | Budget |
| --- | --- |
| Building (Claude Code or chat) | \~$40 |
| Testing runs | \~$10 |
| Demo rehearsals | \~$5 |
| Reserve | \~$45 |

The large reserve leaves room for optional extras such as a logo concept, an SEO checklist or a WhatsApp catalog, but only once the core path works.

**Habits that stretch credits:**

- Set a spend limit in the Console and check usage every evening.
- Use prompt caching for the system prompt and site template.
- Use Haiku wherever strong reasoning is not needed.
- Mock GoDaddy calls during UI work and cache successful runs as JSON fixtures for free replay.
- Share only the relevant function and error with Claude, not whole files.
- Build in small vertical slices to avoid rewriting large files.

## Five-day schedule

**Day 1: Foundations.** Install gddy in the Codespace, add a payment method, create a PAT and practise on the ote environment (suggest, available, quote). Install the gddy agent skill in Claude Code. Create the FastAPI and React skeletons, the wizard shell and Claude call #1.

**Day 2: Domains.** A backend wrapper around the gddy domain commands that parses their JSON, the domain picker with prices, and quote plus purchase behind the Approve button. Handle the 10-minute quote expiry.

**Day 3: The website.** One strong site template, Claude call #2, live preview, Hindi/English toggle, and the packaging step that turns the generated site into a zip meeting GoDaddy's Node.js requirements.

**Day 4: Connect and complete.** Hosting upload, attach and publish with polling, DNS records and connecting the domain, confirm screen, launch kit, and one real end-to-end run on a real, cheap domain.

**Day 5: Polish and demo.** Error states, recorded backup video, README, architecture slide, and 3 to 4 demo rehearsals.

## Demo script (about 4 minutes)

1. **Problem (20s):** launching online takes a week and five tools.
2. **Live input (20s):** type the achaar-in-Lucknow sentence.
3. **Brief and names (40s):** Claude's brief appears, followed by domain suggestions with prices.
4. **Site preview (40s):** a real site appears; switch it to Hindi.
5. **Approval (20s):** nothing is bought until the user clicks Approve.
6. **Go live (40s):** domain purchase, GoDaddy Hosting publish and DNS, then open the real URL.
7. **Launch kit (20s):** social posts and the 30-day checklist.
8. **Impact (20s):** idea to live business in 10 minutes; next steps are payments and email.

**Pre-demo safety:** use a domain registered during rehearsal for the live registration step. Run real suggestions, availability and site generation on stage. If registration is slow or fails, switch to the cached successful run and say so honestly.

## Risks and fallbacks

| Risk | Fallback |
| --- | --- |
| Purchase API unavailable or restricted for your account | Stop at the locked quote and show it. Use a pre-registered domain for DNS and publish. |
| Testing buys real domains and charges your card | Work in the `ote` environment, use `--dry-run` where supported, and buy only one cheap domain for rehearsal. |
| Quote token expires (about 10 minutes) | Ask for a fresh quote right before the purchase. |
| No hosting plan, or the Node.js upload fails | Deploy the site to a free static host and point GoDaddy DNS at it. |
| `gddy` cannot be installed on the backend host | Call GoDaddy's REST API from FastAPI, or run the purchase and publish steps from the Codespace. |
| DNS propagation is slow | Pre-warm DNS on a domain you already own and show the live URL from rehearsal. |
| Credits run low | Replay fixtures, use Haiku for everything except site generation, shorten the template. |
| Scope creep | Cut the launch kit first, then Hindi. Never cut the domain-to-live-URL path. |
| Network failure at the demo | Recorded backup video and replay mode. |

## Pitch adjustment

Drop "agentic" from the story and lead with the outcome: **"Idea to live business in 10 minutes, with AI doing the thinking and GoDaddy making it real."** Judges will care about the real problem, the working end-to-end demo and clear next steps, not the architecture label.

## Fit with typical judging criteria

- **Innovation:** the whole idea-to-URL chain in one guided flow, with a bilingual option.
- **Technical depth:** structured Claude output, the GoDaddy CLI for domains, DNS and hosting, the quote-then-purchase flow and async polling.
- **Real-world impact:** small businesses and creators, including a local-language option.
- **Feasibility:** a small codebase with clear next steps.
- **Demo quality:** a visible wizard, a live URL at the end, and a safe fallback.

## Next step

The stack is set: Python (FastAPI) + React. Start with Day 1: set up the Codespace, install `gddy`, and test suggest, available and quote on the `ote` environment. Then build the project skeleton.

## Sources

- [Set up the CLI](https://developer.godaddy.com/en/docs/api-users/cli/set-up) (GoDaddy Developers)
- [CLI workflow reference](https://developer.godaddy.com/en/docs/api-users/cli/reference) (GoDaddy Developers)
- [Node.js app requirements](https://developer.godaddy.com/en/docs/api-users/hosting/app-requirements) (GoDaddy Developers)

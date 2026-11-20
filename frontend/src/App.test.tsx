// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DomainOffer, Quote, Run } from "./api/types";
import { App } from "./App";

const OFFER: DomainOffer = { name: "achaar1.com", price: 9.19, renewal_price: 11.59, currency: "USD", fees: [] };
const PREMIUM_FEE = { type: "ONE_TIME_PREMIUM_DOMAIN_PURCHASE", currency: "USD", value: 390000, amount: 3900 };

const QUOTE: Quote = {
  domain: "achaar1.com",
  period: 1,
  price: 9.19,
  renewal_price: 11.59,
  currency: "USD",
  fees: [],
  agreements: [{ type: "API_DPA", title: "Domain Purchase Agreement", url: "https://example.test/agreement" }],
  expires_at: new Date(Date.now() + 10 * 60_000).toISOString(),
  demo: true,
};

let runs: Record<string, Run>;
let calls: string[];

function makeRun(overrides: Partial<Run> = {}): Run {
  return {
    id: "r1",
    state: "briefed",
    lang: "en",
    idea: "pickles",
    brief: { audience: "Home cooks", tone: "Warm", tagline: "Pickles like home", name_ideas: ["achaar"] },
    domains: [],
    domain: null,
    quote: null,
    purchase: null,
    regenerations: 0,
    ...overrides,
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

// A tiny fake of the backend, enough to drive the wizard.
function fakeFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const url = String(input).replace(/^\/api/, "");
  const method = init?.method ?? "GET";
  calls.push(`${method} ${url}`);
  const match = /^\/runs\/([^/?]+)(?:\/(\w+))?/.exec(url);

  if (method === "POST" && url === "/runs") {
    runs.r1 = makeRun();
    return Promise.resolve(json(runs.r1, 201));
  }
  const run = match && runs[match[1]];
  if (!match || !run) {
    return Promise.resolve(json({ error: { code: "run_not_found", message: "We couldn't find that session." } }, 404));
  }
  switch (match[2]) {
    case undefined:
      return Promise.resolve(json(run));
    case "domains":
      Object.assign(run, { state: "domains_listed", domains: [OFFER], domain: null });
      return Promise.resolve(json(run));
    case "domain":
      Object.assign(run, { state: "domain_chosen", domain: OFFER });
      return Promise.resolve(json(run));
    case "generate":
      Object.assign(run, { state: "site_generated" });
      return Promise.resolve(json(run));
    case "quote":
      run.quote = QUOTE;
      return Promise.resolve(json(run));
    case "purchase": {
      const body = JSON.parse(String(init?.body));
      if (body.price !== QUOTE.price || !body.agreement_types.includes("API_DPA")) {
        return Promise.resolve(json({ error: { code: "confirmation_mismatch", message: "Please review again." } }, 409));
      }
      Object.assign(run, {
        state: "purchased",
        purchase: {
          domain: QUOTE.domain,
          status: "completed",
          demo: true,
          price: QUOTE.price,
          currency: "USD",
          registration_id: null,
          agreed_at: new Date().toISOString(),
          expires_at: null,
        },
      });
      return Promise.resolve(json(run));
    }
    default:
      return Promise.resolve(json({ error: { code: "x", message: "unexpected" } }, 500));
  }
}

beforeEach(() => {
  runs = {};
  calls = [];
  window.location.hash = "";
  vi.stubGlobal("fetch", vi.fn(fakeFetch));
  // jsdom does not implement the modal methods of <dialog>.
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function startAndReachReview(user: ReturnType<typeof userEvent.setup>) {
  render(<App />);
  await user.type(screen.getByLabelText("What's your business idea?"), "pickles");
  await user.click(screen.getByRole("button", { name: "Create my business summary" }));
  await user.click(await screen.findByLabelText(/achaar1\.com/));
  await user.click(screen.getByRole("button", { name: "Choose this domain" }));
  await screen.findByRole("heading", { name: "Check the price" });
}

describe("homepage", () => {
  it("explains Shuru and starts with the idea form, without the stepper", async () => {
    render(<App />);

    expect(screen.getByRole("heading", { level: 1, name: "Turn one sentence into your own website" })).toBeTruthy();
    expect(screen.getByLabelText("What's your business idea?")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "How it works" })).toBeTruthy();
    expect(screen.queryByRole("navigation", { name: "Progress" })).toBeNull();
    expect(document.title).toBe("Shuru · Turn your idea into a website");
  });

  it("lists only what the flow delivers today", async () => {
    render(<App />);

    const youGet = screen.getByRole("list", { name: "What you get" });
    expect(within(youGet).getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "A business summary and name ideas",
      "Available domains with real prices",
      "A one-page website in English and हिन्दी",
    ]);
    expect(youGet.textContent).not.toMatch(/live/i);
  });

  it("says the site comes in both languages: the form's switch is only for the summary", async () => {
    const user = userEvent.setup();
    render(<App />);
    const frame = () => screen.getByTitle(/Sample site for lucknowachaar\.com/) as HTMLIFrameElement;
    expect(screen.getByText(/Your website comes in both English and/)).toBeTruthy();

    const summaryLanguage = screen.getByRole("group", { name: "Language for your summary" });
    await user.click(within(summaryLanguage).getByRole("button", { name: "हिन्दी" }));
    expect(frame().getAttribute("src")).toBe("/samples/sample-site.en.html");
  });

  it("switches the example's language with its own tab, with no API call", async () => {
    const user = userEvent.setup();
    render(<App />);
    const frame = () => screen.getByTitle(/Sample site for lucknowachaar\.com/) as HTMLIFrameElement;
    const sampleIdea = () => document.querySelector(".sample-idea q") as HTMLElement;
    expect(frame().getAttribute("src")).toBe("/samples/sample-site.en.html");
    expect(frame().getAttribute("sandbox")).toBe("");
    expect(sampleIdea().textContent).toMatch(/homemade achaar in Lucknow/);

    const view = screen.getByRole("group", { name: "View the example in" });
    await user.click(within(view).getByRole("button", { name: "हिन्दी" }));

    expect(frame().getAttribute("src")).toBe("/samples/sample-site.hi.html");
    expect(sampleIdea().textContent).toBe("लखनऊ में घर के बने अचार का कारोबार, ऑनलाइन बिक्री के लिए");
    expect(sampleIdea().lang).toBe("hi");
    expect(calls).toHaveLength(0);
  });

  it("shows the character count only near the limit", async () => {
    const user = userEvent.setup();
    render(<App />);
    const count = document.getElementById("idea-count") as HTMLElement;
    expect(count.className).toBe("sr-only");

    fireEvent.change(screen.getByLabelText("What's your business idea?"), { target: { value: "a".repeat(420) } });
    expect(count.className).toBe("hint");
    await user.type(screen.getByLabelText("What's your business idea?"), "b".repeat(40));
    expect(count.className).toBe("hint warn");
  });

  it("shows the examples in Hindi when Hindi is chosen, and swaps a picked example for its twin", async () => {
    const user = userEvent.setup();
    render(<App />);
    const form = screen.getByRole("form", { name: "Start a new site" });
    const language = within(form).getByRole("group", { name: "Language for your summary" });

    await user.click(within(form).getByRole("button", { name: /yoga classes online for busy/ }));
    await user.click(within(language).getByRole("button", { name: "हिन्दी" }));

    expect(within(form).queryByRole("button", { name: /yoga classes online for busy/ })).toBeNull();
    expect(within(form).getAllByRole("button", { name: /ऑनलाइन/ }).length).toBe(3);
    const idea = screen.getByLabelText("What's your business idea?") as HTMLTextAreaElement;
    expect(idea.value).toBe("व्यस्त ऑफ़िस कर्मचारियों के लिए ऑनलाइन योग कक्षाएँ");
    expect(idea.lang).toBe("hi");

    // Text the user typed themselves is left alone when the language changes.
    await user.clear(idea);
    await user.type(idea, "my own idea");
    await user.click(within(language).getByRole("button", { name: "English" }));
    expect(idea.value).toBe("my own idea");
    expect(within(form).getByRole("button", { name: /homemade achaar in Lucknow/ })).toBeTruthy();
  });

  it("moves to the idea box from the closing call to action", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Start my site" }));

    expect(document.activeElement).toBe(screen.getByLabelText("What's your business idea?"));
  });

  it("opens support from the footer", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Need help? Contact support" }));

    expect(screen.getByText("Hi, need help? We reply within 1-2 days.")).toBeTruthy();
  });

  it("shows the stepper once a run starts", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText("What's your business idea?"), "pickles");
    await user.click(screen.getByRole("button", { name: "Create my business summary" }));

    await screen.findByRole("heading", { name: "Choose your domain" });
    expect(screen.getByRole("navigation", { name: "Progress" })).toBeTruthy();
  });
});

describe("support dialog", () => {
  it("opens from the header, keeps wizard state, and closes on Escape", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText("What's your business idea?"), "pickles");

    expect(screen.queryByText("Contact us")).toBeNull();
    const support = screen.getByRole("button", { name: "Support" });
    await user.click(support);
    expect(screen.getByText("Hi, need help? We reply within 1-2 days.")).toBeTruthy();
    expect(screen.getByLabelText("Your name")).toBeTruthy();

    const dialog = document.querySelector(".support-dialog") as HTMLDialogElement;
    expect(dialog.hasAttribute("open")).toBe(true);
    // Escape fires a cancelable "cancel" event on a native <dialog>.
    fireEvent(dialog, new Event("cancel", { cancelable: true }));
    await waitFor(() => expect(dialog.hasAttribute("open")).toBe(false));
    expect((screen.getByLabelText("What's your business idea?") as HTMLTextAreaElement).value).toBe("pickles");
  });
});

describe("wizard flow", () => {
  it("walks from idea to preview and keeps the step in the URL", async () => {
    const user = userEvent.setup();
    await startAndReachReview(user);
    expect(window.location.hash).toBe("#/run/r1/review");
    expect(screen.getByText("Nothing is purchased yet.")).toBeTruthy();
    expect(screen.getByText(/Renews at \$11\.59/)).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Confirm and build my site" }));
    await screen.findByRole("heading", { name: "Preview your site" });
    expect(window.location.hash).toBe("#/run/r1/preview");

    // Device and language toggles only restyle or re-point the iframe: no API calls.
    const before = calls.length;
    const frame = () => document.querySelector("iframe.preview") as HTMLIFrameElement;
    expect(frame().classList.contains("mobile")).toBe(false);
    await user.click(screen.getByRole("button", { name: "Mobile" }));
    expect(frame().classList.contains("mobile")).toBe(true);
    await user.click(screen.getByRole("button", { name: "हिन्दी" }));
    await user.click(screen.getByRole("button", { name: "Desktop" }));
    expect(frame().classList.contains("mobile")).toBe(false);
    expect(frame().getAttribute("src")).toContain("lang=hi");
    expect(calls.length).toBe(before);
  });

  it("generates the site only after the user confirms", async () => {
    const user = userEvent.setup();
    await startAndReachReview(user);
    expect(calls.some((call) => call.includes("/generate"))).toBe(false);
  });

  it("goes back from Review to Domain without searching again", async () => {
    const user = userEvent.setup();
    await startAndReachReview(user);
    const searches = calls.filter((call) => call.includes("/domains")).length;

    await user.click(screen.getByRole("button", { name: "Pick a different domain" }));

    await screen.findByRole("heading", { name: "Choose your domain" });
    expect(calls.filter((call) => call.includes("/domains")).length).toBe(searches);
    expect((screen.getByLabelText(/achaar1\.com/) as HTMLInputElement).checked).toBe(true);
  });
});

describe("premium domains", () => {
  it("shows the one-time fee in the domain list and on the review screen", async () => {
    const premium = { ...OFFER, name: "achaar1.com", fees: [PREMIUM_FEE] };
    runs.r1 = makeRun({ state: "domains_listed", domains: [premium] });
    window.location.hash = "#/run/r1/domain";
    render(<App />);

    await screen.findByText(/Premium domain: plus a one-time fee of \$3,900\.00/);

    runs.r1 = makeRun({ state: "domain_chosen", domain: premium, domains: [premium] });
    window.location.hash = "#/run/r1/review";
    cleanup();
    render(<App />);
    await screen.findByRole("heading", { name: "Check the price" });
    expect(screen.getByText(/plus a one-time fee of \$3,900\.00, charged when you buy/)).toBeTruthy();
    expect(screen.getByText("$3,909.19")).toBeTruthy(); // 9.19 + 3,900.00
  });

  it("shows nothing extra for an ordinary domain", async () => {
    runs.r1 = makeRun({ state: "domain_chosen", domain: OFFER, domains: [OFFER] });
    window.location.hash = "#/run/r1/review";
    render(<App />);

    await screen.findByRole("heading", { name: "Check the price" });
    expect(screen.queryByText(/Premium domain/)).toBeNull();
    expect(screen.queryByText(/Total first year/)).toBeNull();
  });
});

describe("checkout", () => {
  function openCheckout() {
    runs.r1 = makeRun({ state: "site_generated", domain: OFFER, domains: [OFFER] });
    window.location.hash = "#/run/r1/checkout";
    render(<App />);
  }

  it("gets a quote, needs the agreement ticked, and finishes a demo purchase", async () => {
    const user = userEvent.setup();
    openCheckout();

    await screen.findByRole("heading", { name: "Buy your domain" });
    expect(await screen.findByText(/no domain will be registered/)).toBeTruthy();
    const buy = screen.getByRole("button", { name: "Complete demo purchase" }) as HTMLButtonElement;
    expect(buy.disabled).toBe(true);
    expect(calls).toContain("POST /runs/r1/quote");

    expect(screen.getByRole("link", { name: "Domain Purchase Agreement" }).getAttribute("href")).toBe(
      "https://example.test/agreement",
    );
    await user.click(screen.getByLabelText(/I have read and agree/));
    expect(buy.disabled).toBe(false);
    await user.click(buy);

    await screen.findByRole("heading", { name: "Demo purchase complete" });
    expect(screen.getByText(/\(not charged\)/)).toBeTruthy();
  });

  it("opens the Buy step from the preview", async () => {
    const user = userEvent.setup();
    runs.r1 = makeRun({ state: "site_generated", domain: OFFER, domains: [OFFER] });
    window.location.hash = "#/run/r1/preview";
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Buy domain" }));

    await screen.findByRole("heading", { name: "Buy your domain" });
    expect(window.location.hash).toBe("#/run/r1/checkout");
  });

  it("locks every earlier step after the purchase and shows the site", async () => {
    runs.r1 = makeRun({
      state: "purchased",
      domain: OFFER,
      purchase: {
        domain: "achaar1.com", status: "completed", demo: true, price: 9.19, currency: "USD",
        registration_id: null, agreed_at: new Date().toISOString(), expires_at: null,
      },
    });
    window.location.hash = "#/run/r1/preview";
    render(<App />);

    await screen.findByRole("heading", { name: "Demo purchase complete" });
    await waitFor(() => expect(window.location.hash).toBe("#/run/r1/checkout"));
    const nav = screen.getByRole("navigation", { name: "Progress" });
    expect(within(nav).queryAllByRole("button")).toHaveLength(0);

    expect(document.querySelector("iframe.preview")?.getAttribute("src")).toContain("/api/runs/r1/preview?lang=en");
    expect(screen.getByRole("link", { name: "Open your site in a new tab" }).getAttribute("href")).toContain(
      "/preview?lang=en",
    );
    expect(screen.getByRole("button", { name: "Start a new site" })).toBeTruthy();
  });

  it("shows the confirmation when a purchased run is opened again", async () => {
    runs.r1 = makeRun({
      state: "purchased",
      domain: OFFER,
      purchase: {
        domain: "achaar1.com", status: "completed", demo: true, price: 9.19, currency: "USD",
        registration_id: null, agreed_at: new Date().toISOString(), expires_at: null,
      },
    });
    window.location.hash = "#/run/r1/checkout";
    render(<App />);

    await screen.findByRole("heading", { name: "Demo purchase complete" });
  });

  it("does not quote again while the stored quote is still locked", async () => {
    runs.r1 = makeRun({ state: "site_generated", domain: OFFER, domains: [OFFER], quote: QUOTE });
    window.location.hash = "#/run/r1/checkout";
    render(<App />);

    await screen.findByRole("heading", { name: "Buy your domain" });
    expect(calls.some((call) => call.endsWith("/quote"))).toBe(false);
  });
});

describe("after the idea is submitted", () => {
  it("goes straight to the domain step, which searches by itself", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText("What's your business idea?"), "pickles");
    await user.click(screen.getByRole("button", { name: "Create my business summary" }));

    await screen.findByRole("heading", { name: "Choose your domain" });
    expect(window.location.hash).toBe("#/run/r1/domain");
    expect(screen.queryByRole("button", { name: "Find domains" })).toBeNull();
    expect(screen.getByText("Pickles like home")).toBeTruthy(); // the summary is on this screen
    await screen.findByLabelText(/achaar1\.com/);
    expect(calls.filter((call) => call.includes("/domains"))).toHaveLength(1);
  });

  it("shows the idea read-only when the user goes back to the Idea step", async () => {
    const user = userEvent.setup();
    runs.r1 = makeRun({ state: "domains_listed", domains: [OFFER], idea: "I make pickles" });
    window.location.hash = "#/run/r1/idea";
    render(<App />);

    await screen.findByRole("heading", { name: "Your idea" });
    expect(screen.getByText("I make pickles")).toBeTruthy();
    expect(screen.queryByLabelText("What's your business idea?")).toBeNull(); // no form: the idea cannot be changed
    expect(screen.getByText("Pickles like home")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Back to domains" }));
    await screen.findByRole("heading", { name: "Choose your domain" });
  });

  it("offers to go back to the site once it has been written", async () => {
    runs.r1 = makeRun({ state: "site_generated", domain: OFFER, domains: [OFFER] });
    window.location.hash = "#/run/r1/idea";
    render(<App />);

    await screen.findByRole("heading", { name: "Your idea" });
    expect(screen.getByRole("button", { name: "Back to your site" })).toBeTruthy();
  });
});

describe("domain step business summary", () => {
  async function openDomainStep(user: ReturnType<typeof userEvent.setup>) {
    render(<App />);
    await user.type(screen.getByLabelText("What's your business idea?"), "pickles");
    await user.click(screen.getByRole("button", { name: "Create my business summary" }));
      await screen.findByRole("heading", { name: "Choose your domain" });
  }

  it("shows the tagline and name ideas, with audience and tone folded away", async () => {
    const user = userEvent.setup();
    await openDomainStep(user);

    const summary = screen.getByRole("complementary", { name: "Your business" });
    expect(within(summary).getByText("Pickles like home")).toBeTruthy();
    expect(within(summary).getByRole("button", { name: "achaar" })).toBeTruthy();
    expect(summary.querySelector("details")?.open).toBe(false);
  });

  it("searches for a name idea when it is tapped, and goes back to the default when tapped again", async () => {
    const user = userEvent.setup();
    await openDomainStep(user);
    const chip = screen.getByRole("button", { name: "achaar" });

    await user.click(chip);
    await waitFor(() => expect(calls.some((call) => call.includes("/domains?keyword=achaar"))).toBe(true));
    await waitFor(() => expect(chip.getAttribute("aria-pressed")).toBe("true"));
    expect((screen.getByLabelText("Looking for something else?") as HTMLInputElement).value).toBe("achaar");

    const before = calls.length;
    await user.click(chip);
    await waitFor(() => expect(chip.getAttribute("aria-pressed")).toBe("false"));
    expect(calls.slice(before).some((call) => call.includes("keyword"))).toBe(false);
  });
});

describe("stepper", () => {
  it("lets the user go back to a finished step and marks locked steps after generation", async () => {
    const user = userEvent.setup();
    await startAndReachReview(user);
    const nav = screen.getByRole("navigation", { name: "Progress" });

    await user.click(within(nav).getByRole("button", { name: /Domain/ }));
    await screen.findByRole("heading", { name: "Choose your domain" });
  });

  it("locks Domain and Review once the site is generated", async () => {
    runs.r1 = makeRun({ state: "site_generated", domain: OFFER, domains: [OFFER] });
    window.location.hash = "#/run/r1/preview";
    render(<App />);
    await screen.findByRole("heading", { name: "Preview your site" });
    const nav = screen.getByRole("navigation", { name: "Progress" });

    expect(within(nav).queryByRole("button", { name: /Domain/ })).toBeNull();
    expect(within(nav).queryByRole("button", { name: /Price/ })).toBeNull();
    expect(within(nav).getByRole("button", { name: /Idea/ })).toBeTruthy();
  });
});

describe("resume and locking", () => {
  it("opens a run from the URL on a fresh page load", async () => {
    runs.r1 = makeRun({ state: "domain_chosen", domain: OFFER, domains: [OFFER] });
    window.location.hash = "#/run/r1/review";

    render(<App />);

    await screen.findByRole("heading", { name: "Check the price" });
  });

  it("sends a locked step in the URL to the step the run is at", async () => {
    runs.r1 = makeRun({ state: "site_generated", domain: OFFER, domains: [OFFER] });
    window.location.hash = "#/run/r1/domain";

    render(<App />);

    await screen.findByRole("heading", { name: "Preview your site" });
    await waitFor(() => expect(window.location.hash).toBe("#/run/r1/preview"));
  });

  it("shows a plain error and a way out when the run does not exist", async () => {
    window.location.hash = "#/run/missing/idea";

    render(<App />);

    await screen.findByRole("heading", { name: "We couldn't open that site" });
    expect(screen.getByRole("alert").textContent).toMatch(/couldn't find/);
    expect(screen.getByRole("button", { name: "Start a new site" })).toBeTruthy();
  });
});

describe("logo", () => {
  it("asks before leaving a run, then starts a fresh one", async () => {
    const user = userEvent.setup();
    await startAndReachReview(user);

    await user.click(screen.getByRole("button", { name: "Shuru" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/stays saved/)).toBeTruthy();
    expect(window.location.hash).toBe("#/run/r1/review");

    await user.click(within(dialog).getByRole("button", { name: "Start new site" }));
    await screen.findByRole("heading", { level: 1, name: "Turn one sentence into your own website" });
    expect(window.location.hash).toBe("#/");
  });

  it("keeps the user where they are when they cancel", async () => {
    const user = userEvent.setup();
    await startAndReachReview(user);

    await user.click(screen.getByRole("button", { name: "Shuru" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Keep working" }));

    expect(screen.getByRole("heading", { name: "Check the price" })).toBeTruthy();
    expect(window.location.hash).toBe("#/run/r1/review");
  });

  it("goes home without asking when there is no run", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Shuru" }));

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("heading", { level: 1, name: "Turn one sentence into your own website" })).toBeTruthy();
  });

  it("lets the browser Back button return to the earlier run", async () => {
    const user = userEvent.setup();
    await startAndReachReview(user);
    await user.click(screen.getByRole("button", { name: "Shuru" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Start new site" }));
    await screen.findByRole("heading", { level: 1, name: "Turn one sentence into your own website" });

    window.history.back();

    await screen.findByRole("heading", { name: "Check the price" });
  });
});

// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DomainOffer, Run } from "./api/types";
import { App } from "./App";

const OFFER: DomainOffer = { name: "achaar1.com", price: 9.19, renewal_price: 11.59, currency: "USD" };

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
  await user.type(screen.getByLabelText("Your idea"), "pickles");
  await user.click(screen.getByRole("button", { name: "Create my business summary" }));
  await user.click(await screen.findByRole("button", { name: "Find domains" }));
  await user.click(await screen.findByLabelText(/achaar1\.com/));
  await user.click(screen.getByRole("button", { name: "Choose this domain" }));
  await screen.findByRole("heading", { name: "Review your domain" });
}

describe("support dialog", () => {
  it("opens from the header, keeps wizard state, and closes on Escape", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText("Your idea"), "pickles");

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
    expect((screen.getByLabelText("Your idea") as HTMLTextAreaElement).value).toBe("pickles");
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

    await screen.findByRole("heading", { name: "Pick your domain" });
    expect(calls.filter((call) => call.includes("/domains")).length).toBe(searches);
    expect((screen.getByLabelText(/achaar1\.com/) as HTMLInputElement).checked).toBe(true);
  });
});

describe("domain step business summary", () => {
  async function openDomainStep(user: ReturnType<typeof userEvent.setup>) {
    render(<App />);
    await user.type(screen.getByLabelText("Your idea"), "pickles");
    await user.click(screen.getByRole("button", { name: "Create my business summary" }));
    await user.click(await screen.findByRole("button", { name: "Find domains" }));
    await screen.findByRole("heading", { name: "Pick your domain" });
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
    await screen.findByRole("heading", { name: "Pick your domain" });
  });

  it("locks Domain and Review once the site is generated", async () => {
    runs.r1 = makeRun({ state: "site_generated", domain: OFFER, domains: [OFFER] });
    window.location.hash = "#/run/r1/preview";
    render(<App />);
    await screen.findByRole("heading", { name: "Preview your site" });
    const nav = screen.getByRole("navigation", { name: "Progress" });

    expect(within(nav).queryByRole("button", { name: /Domain/ })).toBeNull();
    expect(within(nav).queryByRole("button", { name: /Review/ })).toBeNull();
    expect(within(nav).getByRole("button", { name: /Idea/ })).toBeTruthy();
  });
});

describe("resume and locking", () => {
  it("opens a run from the URL on a fresh page load", async () => {
    runs.r1 = makeRun({ state: "domain_chosen", domain: OFFER, domains: [OFFER] });
    window.location.hash = "#/run/r1/review";

    render(<App />);

    await screen.findByRole("heading", { name: "Review your domain" });
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
    await screen.findByRole("heading", { name: "What's your business idea?" });
    expect(window.location.hash).toBe("#/");
  });

  it("keeps the user where they are when they cancel", async () => {
    const user = userEvent.setup();
    await startAndReachReview(user);

    await user.click(screen.getByRole("button", { name: "Shuru" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Keep working" }));

    expect(screen.getByRole("heading", { name: "Review your domain" })).toBeTruthy();
    expect(window.location.hash).toBe("#/run/r1/review");
  });

  it("goes home without asking when there is no run", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Shuru" }));

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("heading", { name: "What's your business idea?" })).toBeTruthy();
  });

  it("lets the browser Back button return to the earlier run", async () => {
    const user = userEvent.setup();
    await startAndReachReview(user);
    await user.click(screen.getByRole("button", { name: "Shuru" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Start new site" }));
    await screen.findByRole("heading", { name: "What's your business idea?" });

    window.history.back();

    await screen.findByRole("heading", { name: "Review your domain" });
  });
});

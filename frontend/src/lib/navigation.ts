import type { Run } from "../api/types";

export type Step = "idea" | "domain" | "review" | "preview" | "checkout";

export const STEPS: { id: Step; label: string }[] = [
  { id: "idea", label: "Idea" },
  { id: "domain", label: "Domain" },
  { id: "review", label: "Review" },
  { id: "preview", label: "Preview" },
  { id: "checkout", label: "Buy" },
];

const STEP_ORDER = STEPS.map((step) => step.id);

export function stepIndex(step: Step): number {
  return STEP_ORDER.indexOf(step);
}

/** The step a run is naturally waiting at, given how far it has got. */
export function naturalStep(run: Run): Step {
  switch (run.state) {
    case "briefed":
    case "domains_listed":
      return "domain";
    case "domain_chosen":
      return "review";
    case "site_generated":
      return "preview";
    case "purchasing":
    case "purchased":
      return "checkout";
  }
}

/** Whether the site is not written yet, so the domain can still be changed. */
function isBeforeSite(run: Run): boolean {
  return run.state !== "site_generated" && run.state !== "purchasing" && run.state !== "purchased";
}

/** Whether the domain purchase has started. From then on only the Buy step is open. */
export function isBought(run: Run): boolean {
  return run.state === "purchasing" || run.state === "purchased";
}

/**
 * Which steps the user may open. Once the site is generated the domain is locked (the backend
 * does not allow changing it), so only Idea (read-only), Preview and Buy stay open. Once the
 * domain is being bought or is bought, everything before Buy is locked: only Buy stays open.
 */
export function isStepAvailable(step: Step, run: Run | null): boolean {
  if (!run) return step === "idea";
  if (isBought(run)) return step === "checkout";
  switch (step) {
    case "idea":
      return true;
    case "domain":
      return isBeforeSite(run);
    case "review":
      return run.state === "domain_chosen";
    case "preview":
    case "checkout":
      return !isBeforeSite(run);
  }
}

/** Why a step cannot be opened right now, in plain language. */
export function unavailableHint(step: Step, run: Run | null): string {
  if (!run) return "Describe your idea first.";
  if (isBought(run)) return "Locked once your domain is bought. Start over to make a new site.";
  if (!isBeforeSite(run)) return "Locked once your site is written. Start over to change it.";
  if (step === "review") return "Choose a domain first.";
  if (step === "preview" || step === "checkout") return "Confirm your domain first.";
  return "";
}

export type StepStatus = "current" | "done" | "next" | "upcoming";

/** How a step is drawn in the stepper. "next" is the step the run is waiting at. */
export function stepStatus(step: Step, current: Step, run: Run | null): StepStatus {
  if (step === current) return "current";
  if (!run) return "upcoming";
  const next = naturalStep(run);
  if (step === next) return "next";
  return stepIndex(step) < stepIndex(next) ? "done" : "upcoming";
}

// --- Routing: the run and step live in the URL hash, e.g. `#/run/abc123/review` ---

export interface Route {
  runId: string | null;
  step: Step | null;
}

const RUN_ROUTE = /^#\/run\/([A-Za-z0-9_-]+)(?:\/(idea|domain|review|preview|checkout))?$/;

export function parseRoute(hash: string): Route {
  const match = RUN_ROUTE.exec(hash);
  if (!match) return { runId: null, step: null };
  return { runId: match[1], step: (match[2] as Step | undefined) ?? null };
}

export function routeHash(runId: string | null, step: Step): string {
  return runId ? `#/run/${runId}/${step}` : "#/";
}

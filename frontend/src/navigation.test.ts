import { describe, expect, it } from "vitest";
import type { Run, RunState } from "./api/types";
import {
  isStepAvailable,
  naturalStep,
  parseRoute,
  routeHash,
  stepStatus,
  unavailableHint,
  type Step,
} from "./navigation";

function runIn(state: RunState): Run {
  return {
    id: "abc",
    state,
    lang: "en",
    idea: "x",
    brief: { audience: "a", tone: "t", tagline: "g", name_ideas: [] },
    domains: [],
    domain: null,
    regenerations: 0,
  };
}

const ALL: Step[] = ["idea", "domain", "review", "preview"];
const open = (state: RunState) => ALL.filter((step) => isStepAvailable(step, runIn(state)));

describe("naturalStep", () => {
  it.each([
    ["briefed", "domain"],
    ["domains_listed", "domain"],
    ["domain_chosen", "review"],
    ["site_generated", "preview"],
  ] as const)("%s waits at %s", (state, step) => {
    expect(naturalStep(runIn(state))).toBe(step);
  });
});

describe("isStepAvailable", () => {
  it("only offers Idea when there is no run", () => {
    expect(ALL.filter((step) => isStepAvailable(step, null))).toEqual(["idea"]);
  });

  it("opens steps as the run progresses", () => {
    expect(open("briefed")).toEqual(["idea", "domain"]);
    expect(open("domains_listed")).toEqual(["idea", "domain"]);
    expect(open("domain_chosen")).toEqual(["idea", "domain", "review"]);
  });

  it("locks Domain and Review once the site is generated", () => {
    expect(open("site_generated")).toEqual(["idea", "preview"]);
  });
});

describe("unavailableHint", () => {
  it("explains the lock after generation", () => {
    expect(unavailableHint("domain", runIn("site_generated"))).toMatch(/Start over/);
  });

  it("tells the user what to do first", () => {
    expect(unavailableHint("review", runIn("briefed"))).toBe("Choose a domain first.");
    expect(unavailableHint("preview", runIn("domain_chosen"))).toBe("Confirm your domain first.");
    expect(unavailableHint("domain", null)).toBe("Describe your idea first.");
  });
});

describe("stepStatus", () => {
  it("marks earlier steps done and the waiting step next", () => {
    const run = runIn("domain_chosen");
    expect(stepStatus("idea", "review", run)).toBe("done");
    expect(stepStatus("domain", "review", run)).toBe("done");
    expect(stepStatus("review", "review", run)).toBe("current");
    expect(stepStatus("preview", "review", run)).toBe("upcoming");
  });

  it("shows the next step while viewing an earlier one", () => {
    expect(stepStatus("domain", "idea", runIn("briefed"))).toBe("next");
  });

  it("has nothing done without a run", () => {
    expect(stepStatus("domain", "idea", null)).toBe("upcoming");
  });
});

describe("routes", () => {
  it.each([
    ["#/run/abc123/review", { runId: "abc123", step: "review" }],
    ["#/run/abc123", { runId: "abc123", step: null }],
    ["#/", { runId: null, step: null }],
    ["", { runId: null, step: null }],
    ["#/run/abc123/bogus", { runId: null, step: null }],
    ["#/run/a b/idea", { runId: null, step: null }],
  ])("parses %j", (hash, expected) => {
    expect(parseRoute(hash)).toEqual(expected);
  });

  it("round-trips", () => {
    expect(parseRoute(routeHash("abc", "preview"))).toEqual({ runId: "abc", step: "preview" });
    expect(routeHash(null, "idea")).toBe("#/");
  });
});

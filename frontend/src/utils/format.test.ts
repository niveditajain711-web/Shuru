import { describe, expect, it } from "vitest";
import { totalWithFees } from "./format";

const fee = { type: "ONE_TIME_PREMIUM_DOMAIN_PURCHASE", currency: "USD", value: 390000, amount: 3900 };

describe("totalWithFees", () => {
  it("adds the premium fees to the registration price", () => {
    expect(totalWithFees(12, [fee], "USD")).toBe(3912);
    expect(totalWithFees(12, [fee, { ...fee, amount: 100 }], "USD")).toBe(4012);
  });

  it("has no total for an ordinary domain, where the price already is the total", () => {
    expect(totalWithFees(12, [], "USD")).toBeNull();
  });

  it("has no total when a fee is in another currency", () => {
    expect(totalWithFees(12, [{ ...fee, currency: "EUR" }], "USD")).toBeNull();
  });
});

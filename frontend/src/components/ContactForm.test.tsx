// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ContactForm } from "./ContactForm";

let bodies: unknown[];
let status: number;

beforeEach(() => {
  bodies = [];
  status = 200;
  vi.stubGlobal(
    "fetch",
    vi.fn((_url: string, init?: RequestInit) => {
      bodies.push(JSON.parse(String(init?.body)));
      const body = status === 200 ? { ok: true } : { error: { code: "mail_failed", message: "We couldn't send your message just now." } };
      return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function fill(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Your name"), "Asha");
  await user.type(screen.getByLabelText("Your email"), "asha@example.com");
  await user.type(screen.getByLabelText("Message"), "Hello");
}

describe("ContactForm", () => {
  it("keeps Send disabled until every field is filled", async () => {
    const user = userEvent.setup();
    render(<ContactForm />);
    const send = screen.getByRole("button", { name: "Send message" }) as HTMLButtonElement;
    expect(send.disabled).toBe(true);
    await fill(user);
    expect(send.disabled).toBe(false);
  });

  it("posts the message and confirms", async () => {
    const user = userEvent.setup();
    render(<ContactForm />);
    await fill(user);
    await user.click(screen.getByRole("button", { name: "Send message" }));
    await screen.findByText(/Your message has been sent/);
    expect(bodies).toEqual([{ name: "Asha", email: "asha@example.com", message: "Hello", website: "" }]);
  });

  it("shows a plain error and keeps what was typed", async () => {
    status = 502;
    const user = userEvent.setup();
    render(<ContactForm />);
    await fill(user);
    await user.click(screen.getByRole("button", { name: "Send message" }));
    expect((await screen.findByRole("alert")).textContent).toContain("couldn't send your message");
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("Hello");
  });
});

// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import App from "./App";
import { api } from "./api";
import type { Answer } from "./types";

vi.mock("./api", () => ({ api: vi.fn(), exportJson: vi.fn() }));
const request = vi.mocked(api);
const question = "The Cedar trial enrolled 120 adults.";
const answer: Answer = {
  id: "run-1",
  question,
  answer: question,
  answer_kind: "claim_check",
  variant: "verified",
  abstained: false,
  counts: { supported: 1 },
  generation: { provider: "extractive", model: "local", usage: {} },
  timings: {},
  latency_ms: 500,
  notes: [],
  audit: {},
  claims: [
    {
      id: "claim-1",
      text: question,
      verdict: "supported",
      explanation: "The source agrees.",
      citations: [
        {
          chunk_id: "chunk-1",
          document_id: "doc-1",
          document_name: "trial.pdf",
          page_number: 1,
          quote: question,
          integrity: true,
          relation: "supported",
        },
      ],
      counter_evidence: [],
    },
  ],
};
let mobile = false;
let saved = false;

beforeEach(() => {
  mobile = false;
  saved = false;
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      matches: mobile,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
  vi.stubGlobal("requestAnimationFrame", (fn: FrameRequestCallback) => {
    fn(0);
    return 0;
  });
  request.mockReset();
  request.mockImplementation(async (path) => {
    if (path === "/health")
      return {
        status: "ok",
        gemini_configured: false,
        ollama_available: false,
      };
    if (path === "/workspace") return {};
    if (path === "/documents")
      return {
        documents: [
          {
            id: "doc-1",
            name: "trial.pdf",
            page_count: 1,
            byte_count: 1200,
            sha256: "abc",
            created_at: "2026-10-16",
          },
        ],
      };
    if (path === "/runs")
      return { runs: saved ? [{ ...answer, created_at: "2026-10-16" }] : [] };
    if (path === "/verify" || path === "/ask") {
      saved = true;
      return answer;
    }
    if (path === "/runs/run-1") return answer;
    if (path === "/documents/doc-1/pages/1") return { text: question };
    throw new Error(`Unexpected request: ${path}`);
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

async function start() {
  const result = render(<App />);
  await screen.findByText("Workspace ready");
  await waitFor(() =>
    expect(
      screen.getByRole("textbox", { name: "Your research question" }),
    ).toBeEnabled(),
  );
  return result;
}

it("collapses the desktop sidebar and lets the source picker reopen it", async () => {
  const { container } = await start();
  fireEvent.click(screen.getByRole("button", { name: "Close sidebar" }));
  expect(container.querySelector(".navigation")).toHaveAttribute("inert");
  expect(screen.getByRole("button", { name: "Open sidebar" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Choose sources (1 selected)" }),
  );
  expect(container.querySelector(".navigation")).not.toHaveAttribute("inert");
  expect(container.querySelector(".main-shell")).not.toHaveAttribute("inert");
});

it("isolates the mobile drawer and closes it with Escape", async () => {
  mobile = true;
  const { container } = await start();
  expect(container.querySelector(".navigation")).toHaveAttribute("inert");
  fireEvent.click(screen.getByRole("button", { name: "Open sidebar" }));
  expect(container.querySelector(".main-shell")).toHaveAttribute("inert");
  expect(screen.getByRole("button", { name: "Close sidebar" })).toHaveFocus();
  fireEvent.keyDown(window, { key: "Escape" });
  expect(container.querySelector(".main-shell")).not.toHaveAttribute("inert");
  expect(container.querySelector(".navigation")).toHaveAttribute("inert");
});

it("sends on Enter, clears a successful draft, and reopens the saved claim check", async () => {
  await start();
  fireEvent.click(screen.getByRole("button", { name: "Check a claim" }));
  const input = screen.getByRole("textbox", { name: "Your research question" });
  fireEvent.change(input, { target: { value: question } });
  fireEvent.keyDown(input, { key: "Enter" });
  await screen.findByText("Supported by source");
  expect(input).toHaveValue("");
  const submission = request.mock.calls.find(([path]) => path === "/verify");
  expect(JSON.parse(submission?.[1]?.body as string)).toMatchObject({
    question,
    document_ids: ["doc-1"],
  });
  fireEvent.click(screen.getByRole("button", { name: "New question" }));
  expect(screen.queryByText("Supported by source")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: question }));
  await screen.findByText("Supported by source");
  expect(screen.getByRole("button", { name: "Check a claim" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(input).toHaveValue("");
});

it("keeps Shift+Enter and IME composition from sending a request", async () => {
  await start();
  const input = screen.getByRole("textbox", { name: "Your research question" });
  fireEvent.change(input, { target: { value: question } });
  fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
  fireEvent.keyDown(input, { key: "Enter", isComposing: true });
  expect(
    request.mock.calls.some(([path]) => path === "/ask" || path === "/verify"),
  ).toBe(false);
  expect(input).toHaveValue(question);
});

it("keeps the draft when a request fails so the user can retry", async () => {
  await start();
  const previous = request.getMockImplementation()!;
  request.mockImplementation(async (...args) => {
    if (args[0] === "/ask")
      throw new Error("The request failed. Please try again.");
    return previous(...args);
  });
  const input = screen.getByRole("textbox", { name: "Your research question" });
  fireEvent.change(input, { target: { value: question } });
  fireEvent.click(screen.getByRole("button", { name: "Ask question" }));
  await screen.findByRole("alert");
  expect(input).toHaveValue(question);
  expect(screen.getByRole("button", { name: "Ask question" })).toBeEnabled();
});

it.each(["verify", "extractive", "gemini"])(
  "only sends the entered key when generation needs Gemini (%s)",
  async (mode) => {
    // jsdom has no native dialog implementation; emulate opening it for form interactions.
    Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
      configurable: true,
      value: function (this: HTMLDialogElement) {
        this.setAttribute("open", "");
      },
    });
    await start();
    fireEvent.click(screen.getByRole("button", { name: /AI settings/ }));
    fireEvent.change(screen.getByLabelText("Answer engine"), {
      target: { value: "gemini" },
    });
    fireEvent.change(screen.getByLabelText("Gemini API key"), {
      target: { value: "fictional-ui-boundary-key" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
    if (mode === "extractive") {
      fireEvent.click(screen.getByRole("button", { name: /AI settings/ }));
      fireEvent.change(screen.getByLabelText("Answer engine"), {
        target: { value: "extractive" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
    }
    if (mode === "verify")
      fireEvent.click(screen.getByRole("button", { name: "Check a claim" }));
    fireEvent.change(
      screen.getByRole("textbox", { name: "Your research question" }),
      { target: { value: question } },
    );
    fireEvent.click(screen.getByRole("button", { name: "Ask question" }));
    await screen.findByText("Supported by source");
    const path = mode === "verify" ? "/verify" : "/ask";
    const submission = request.mock.calls.find(([url]) => url === path)!;
    const headers = new Headers(submission[1]?.headers);
    expect(headers.get("X-Gemini-Key")).toBe(
      mode === "gemini" ? "fictional-ui-boundary-key" : null,
    );
    expect(submission[1]?.body).not.toContain("fictional-ui-boundary-key");
  },
);

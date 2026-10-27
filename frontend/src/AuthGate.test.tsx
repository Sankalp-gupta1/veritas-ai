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
import AuthGate from "./AuthGate";
import { api } from "./api";

vi.mock("./api", () => ({ api: vi.fn(), exportJson: vi.fn() }));
vi.mock("./App", () => ({
  default: () => <div>Private research workspace</div>,
}));
const request = vi.mocked(api);
const account = {
  id: "alice",
  email: "alice@example.com",
  email_verified: false,
  workspace_id: "workspace-a",
  cloud_enabled: false,
  save_history: false,
  idle_timeout_minutes: 30,
};
beforeEach(() => {
  request.mockReset();
  request.mockImplementation(async (path) => {
    if (path === "/auth/session")
      return { account: null, legacy_available: false };
    if (path === "/auth/register")
      return {
        account,
        recovery_code: "fictional-high-entropy-code-for-ui-test",
      };
    throw new Error("Unexpected request");
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("requires a matching confirmation and acknowledgement of the recovery code", async () => {
  render(<AuthGate />);
  await screen.findByText("Make room for good questions.");
  const password = "a memorable fixture passphrase!";
  fireEvent.change(screen.getByLabelText("Email address"), {
    target: { value: "alice@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: password },
  });
  fireEvent.change(screen.getByLabelText("Confirm password"), {
    target: { value: "different fixture passphrase" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Create my private workspace" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "The passwords do not match.",
  );
  expect(request.mock.calls.some(([path]) => path === "/auth/register")).toBe(
    false,
  );
  fireEvent.change(screen.getByLabelText("Confirm password"), {
    target: { value: password },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Create my private workspace" }),
  );
  await screen.findByText("One last step. Keep your way back in.");
  expect(
    screen.getByRole("button", { name: "Open my workspace" }),
  ).toBeDisabled();
  expect(screen.queryByText("Private research workspace")).toBeNull();
  fireEvent.click(
    screen.getByRole("checkbox", {
      name: "I have saved my recovery code safely.",
    }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Open my workspace" }));
  expect(await screen.findByText("Private research workspace")).toBeVisible();
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
});

it("clears the workspace on server session expiry", async () => {
  request.mockResolvedValue({ account, legacy_available: false });
  render(<AuthGate />);
  await screen.findByText("Private research workspace");
  fireEvent(window, new Event("veritas-session-ended"));
  await waitFor(() =>
    expect(screen.queryByText("Private research workspace")).toBeNull(),
  );
  expect(screen.getByText("Welcome back.")).toBeVisible();
});

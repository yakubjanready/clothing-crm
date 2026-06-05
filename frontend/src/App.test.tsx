import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import i18n from "@/lib/i18n";
import { useAuthStore } from "@/stores/auth";

describe("<App />", () => {
  beforeEach(async () => {
    // Test izolyatsiyasi — har test boshida log out
    useAuthStore.getState().logout();
    localStorage.clear();
    await i18n.changeLanguage("uz");
    vi.stubGlobal(
      "matchMedia",
      vi.fn((q: string) => ({
        matches: false,
        media: q,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("redirects unauthenticated user to /login", async () => {
    render(<App />);
    await waitFor(() => {
      expect(document.querySelector("input#email")).not.toBeNull();
      expect(document.querySelector("input#password")).not.toBeNull();
    });
  });

  it("login form accepts input", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => {
      expect(document.querySelector("input#email")).not.toBeNull();
    });
    const email = document.querySelector<HTMLInputElement>("input#email")!;
    const pass = document.querySelector<HTMLInputElement>("input#password")!;
    await user.type(email, "test@example.com");
    await user.type(pass, "secret");
    expect(email.value).toBe("test@example.com");
    expect(pass.value).toBe("secret");
  });
});

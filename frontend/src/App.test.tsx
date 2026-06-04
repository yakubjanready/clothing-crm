import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("<App />", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            status: "ok",
            app: "clothing-crm",
            env: "test",
            version: "0.1.0",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders title and pings /health on mount", async () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: /Ulgurji Kiyim-kechak CRM/i }),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("health-status")).toHaveTextContent("ok");
    });

    expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/\/health$/));
  });
});

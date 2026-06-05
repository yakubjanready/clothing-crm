import { beforeEach, describe, expect, it } from "vitest";

import { useAuthStore, type AuthUser } from "./auth";

const FAKE_USER: AuthUser = {
  id: "u1",
  email: "admin@example.com",
  full_name: "Admin",
  is_active: true,
  roles: [{ id: "r1", name: "admin", description: "" }],
};

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  it("starts unauthenticated", () => {
    const s = useAuthStore.getState();
    expect(s.accessToken).toBeNull();
    expect(s.user).toBeNull();
  });

  it("login sets tokens + user", () => {
    useAuthStore.getState().login("a", "r", FAKE_USER);
    const s = useAuthStore.getState();
    expect(s.accessToken).toBe("a");
    expect(s.refreshToken).toBe("r");
    expect(s.user?.email).toBe("admin@example.com");
  });

  it("hasRole detects admin", () => {
    useAuthStore.getState().login("a", "r", FAKE_USER);
    expect(useAuthStore.getState().hasRole("admin")).toBe(true);
    expect(useAuthStore.getState().hasRole("courier")).toBe(false);
  });

  it("logout clears state", () => {
    useAuthStore.getState().login("a", "r", FAKE_USER);
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
  });
});

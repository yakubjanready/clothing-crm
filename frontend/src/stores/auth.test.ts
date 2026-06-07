import { beforeEach, describe, expect, it } from "vitest";

import { useAuthStore, type AuthUser } from "./auth";

const FAKE_USER: AuthUser = {
  id: "u1",
  email: "admin@example.com",
  full_name: "Admin",
  is_active: true,
  roles: [{ id: "r1", name: "admin", description: "" }],
};

const PERMS = ["user:read", "user:write", "hr:read"];

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  it("starts unauthenticated", () => {
    const s = useAuthStore.getState();
    expect(s.accessToken).toBeNull();
    expect(s.user).toBeNull();
    expect(s.permissionCodes).toEqual([]);
  });

  it("login sets tokens + user + permissions", () => {
    useAuthStore.getState().login("a", "r", FAKE_USER, PERMS);
    const s = useAuthStore.getState();
    expect(s.accessToken).toBe("a");
    expect(s.refreshToken).toBe("r");
    expect(s.user?.email).toBe("admin@example.com");
    expect(s.permissionCodes).toEqual(PERMS);
  });

  it("hasRole detects admin", () => {
    useAuthStore.getState().login("a", "r", FAKE_USER, PERMS);
    expect(useAuthStore.getState().hasRole("admin")).toBe(true);
    expect(useAuthStore.getState().hasRole("courier")).toBe(false);
  });

  it("hasPermission returns true only for granted codes", () => {
    useAuthStore.getState().login("a", "r", FAKE_USER, PERMS);
    const s = useAuthStore.getState();
    expect(s.hasPermission("user:read")).toBe(true);
    expect(s.hasPermission("warehouse:read")).toBe(false);
  });

  it("hasAnyPermission: empty list means open access", () => {
    useAuthStore.getState().login("a", "r", FAKE_USER, []);
    expect(useAuthStore.getState().hasAnyPermission([])).toBe(true);
  });

  it("hasAnyPermission: at least one match unlocks", () => {
    useAuthStore.getState().login("a", "r", FAKE_USER, PERMS);
    expect(useAuthStore.getState().hasAnyPermission(["warehouse:read", "hr:read"])).toBe(true);
    expect(useAuthStore.getState().hasAnyPermission(["warehouse:read", "order:write"])).toBe(false);
  });

  it("logout clears state including permissions", () => {
    useAuthStore.getState().login("a", "r", FAKE_USER, PERMS);
    useAuthStore.getState().logout();
    const s = useAuthStore.getState();
    expect(s.accessToken).toBeNull();
    expect(s.user).toBeNull();
    expect(s.permissionCodes).toEqual([]);
  });
});

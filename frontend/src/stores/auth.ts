import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: { id: string; name: string; description?: string | null }[];
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  permissionCodes: string[];
  login: (access: string, refresh: string, user: AuthUser, permissions: string[]) => void;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: AuthUser) => void;
  setPermissions: (codes: string[]) => void;
  logout: () => void;
  hasRole: (name: string) => boolean;
  hasPermission: (code: string) => boolean;
  hasAnyPermission: (codes: readonly string[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      permissionCodes: [],
      login: (access, refresh, user, permissions) =>
        set({ accessToken: access, refreshToken: refresh, user, permissionCodes: permissions }),
      setTokens: (access, refresh) => set({ accessToken: access, refreshToken: refresh }),
      setUser: (user) => set({ user }),
      setPermissions: (codes) => set({ permissionCodes: codes }),
      logout: () => set({ user: null, accessToken: null, refreshToken: null, permissionCodes: [] }),
      hasRole: (name) => get().user?.roles.some((r) => r.name === name) ?? false,
      hasPermission: (code) => get().permissionCodes.includes(code),
      hasAnyPermission: (codes) => {
        if (codes.length === 0) return true;
        const set = new Set(get().permissionCodes);
        return codes.some((c) => set.has(c));
      },
    }),
    {
      name: "crm-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        permissionCodes: state.permissionCodes,
      }),
    },
  ),
);

export const useIsAuthenticated = () => useAuthStore((s) => Boolean(s.accessToken && s.user));
export const usePermissions = () => useAuthStore((s) => s.permissionCodes);

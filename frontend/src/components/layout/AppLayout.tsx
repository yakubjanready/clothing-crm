import { useEffect } from "react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

export function AppLayout() {
  const setPermissions = useAuthStore((s) => s.setPermissions);
  const hasUser = useAuthStore((s) => Boolean(s.user));
  const permCount = useAuthStore((s) => s.permissionCodes.length);

  // Persist'da eski login bo'lsa permissionCodes bo'sh bo'lishi mumkin —
  // sahifa yuklanganda /users/me/permissions chaqirib to'ldiramiz.
  useEffect(() => {
    if (hasUser && permCount === 0) {
      api
        .get<string[]>("/users/me/permissions")
        .then((r) => setPermissions(r.data))
        .catch(() => {
          /* 401 bo'lsa interceptor logout qiladi */
        });
    }
  }, [hasUser, permCount, setPermissions]);

  return (
    <div className="flex min-h-screen w-full bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

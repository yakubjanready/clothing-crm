import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useLocation } from "react-router-dom";

import { NAV_ITEMS, type NavItem } from "@/components/layout/nav-items";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

function isActiveParent(item: NavItem, pathname: string): boolean {
  if (pathname === item.to) return true;
  if (item.to !== "/" && pathname.startsWith(item.to + "/")) return true;
  return Boolean(item.children?.some((c) => isActiveParent(c, pathname)));
}

function NavLeaf({ item }: { item: NavItem }) {
  const { t } = useTranslation();
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.to === "/"}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
          "hover:bg-accent hover:text-accent-foreground",
          isActive && "bg-accent font-medium text-accent-foreground",
        )
      }
    >
      <Icon className="h-4 w-4" />
      <span>{t(item.i18nKey)}</span>
    </NavLink>
  );
}

function NavGroup({ item }: { item: NavItem }) {
  const { t } = useTranslation();
  const location = useLocation();
  const [open, setOpen] = useState(() => isActiveParent(item, location.pathname));
  const Icon = item.icon;

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition-colors",
          "hover:bg-accent hover:text-accent-foreground",
          isActiveParent(item, location.pathname) && "text-foreground",
        )}
      >
        <span className="flex items-center gap-3">
          <Icon className="h-4 w-4" />
          {t(item.i18nKey)}
        </span>
        <ChevronDown
          className={cn("h-4 w-4 shrink-0 transition-transform", open && "rotate-180")}
        />
      </button>
      {open && item.children && (
        <div className="ml-7 mt-1 space-y-1 border-l pl-2">
          {item.children.map((c) => (
            <NavLeaf key={c.to} item={c} />
          ))}
        </div>
      )}
    </div>
  );
}

export function SidebarContent() {
  return (
    <nav className="flex h-full flex-col gap-1 p-4">
      <div className="px-2 pb-4">
        <div className="flex items-center gap-2">
          <div className="grid h-9 w-9 place-items-center rounded-md bg-primary text-primary-foreground">
            <span className="text-sm font-bold">UK</span>
          </div>
          <div>
            <div className="text-sm font-semibold">Ulgurji CRM</div>
            <div className="text-xs text-muted-foreground">Kiyim-kechak</div>
          </div>
        </div>
      </div>
      <Separator className="mb-2" />
      <div className="flex-1 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) =>
          item.children ? (
            <NavGroup key={item.to} item={item} />
          ) : (
            <NavLeaf key={item.to} item={item} />
          ),
        )}
      </div>
    </nav>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden h-screen w-64 shrink-0 border-r bg-card md:block">
      <SidebarContent />
    </aside>
  );
}

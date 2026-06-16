import { ChevronDown } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useLocation } from "react-router-dom";

import { filterNav, NAV_ITEMS, type NavItem } from "@/components/layout/nav-items";
import { cn } from "@/lib/utils";
import { usePermissions } from "@/stores/auth";

function isActiveParent(item: NavItem, pathname: string): boolean {
  if (pathname === item.to) return true;
  if (item.to !== "/" && pathname.startsWith(item.to + "/")) return true;
  return Boolean(item.children?.some((c) => isActiveParent(c, pathname)));
}

function NavLeaf({ item, nested = false }: { item: NavItem; nested?: boolean }) {
  const { t } = useTranslation();
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.to === "/"}
      className={({ isActive }) =>
        cn(
          "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-200",
          "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
          nested && "py-1.5 text-[0.84rem]",
          isActive &&
            "bg-accent font-medium text-foreground shadow-sm before:absolute before:left-0 before:top-1/2 before:h-5 before:w-[3px] before:-translate-y-1/2 before:rounded-r-full before:bg-gold",
        )
      }
    >
      <Icon
        className={cn(
          "h-[1.05rem] w-[1.05rem] shrink-0 transition-colors group-hover:text-gold",
          nested && "h-4 w-4",
        )}
      />
      <span className="truncate">{t(item.i18nKey)}</span>
    </NavLink>
  );
}

function NavGroup({ item }: { item: NavItem }) {
  const { t } = useTranslation();
  const location = useLocation();
  const active = isActiveParent(item, location.pathname);
  const [open, setOpen] = useState(() => active);
  const Icon = item.icon;

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-all duration-200",
          "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
          active && "text-foreground",
        )}
      >
        <span className="flex items-center gap-3">
          <Icon className={cn("h-[1.05rem] w-[1.05rem] shrink-0", active && "text-gold")} />
          {t(item.i18nKey)}
        </span>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-muted-foreground/70 transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>
      {open && item.children && (
        <div className="ml-[1.4rem] mt-1 space-y-0.5 border-l border-border/70 pl-3">
          {item.children.map((c) => (
            <NavLeaf key={c.to} item={c} nested />
          ))}
        </div>
      )}
    </div>
  );
}

export function SidebarContent() {
  const perms = usePermissions();
  const visibleItems = useMemo(() => filterNav(NAV_ITEMS, new Set(perms)), [perms]);

  return (
    <nav className="flex h-full flex-col">
      {/* Brend bloki */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-primary text-primary-foreground shadow-md ring-1 ring-gold/30">
          <span className="font-display text-base font-semibold tracking-tight">UK</span>
        </div>
        <div className="min-w-0">
          <div className="font-display text-[1.05rem] font-semibold leading-tight tracking-tight">
            Remodul <span className="text-gold">CRM</span>
          </div>
          <div className="text-[0.7rem] uppercase tracking-[0.18em] text-muted-foreground">
            Kiyim-kechak
          </div>
        </div>
      </div>

      <div className="mx-5 mb-2 h-px bg-gradient-to-r from-transparent via-border to-transparent" />

      <div className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        {visibleItems.map((item) =>
          item.children ? (
            <NavGroup key={item.to} item={item} />
          ) : (
            <NavLeaf key={item.to} item={item} />
          ),
        )}
      </div>

      <div className="mx-5 mb-4 mt-2 rounded-lg border border-border/70 bg-grain px-3 py-3">
        <p className="text-[0.7rem] leading-relaxed text-muted-foreground">
          <span className="font-medium text-foreground">Premium</span> remodul savdo boshqaruvi
        </p>
      </div>
    </nav>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden h-screen w-64 shrink-0 border-r border-border bg-card md:sticky md:top-0 md:block">
      <SidebarContent />
    </aside>
  );
}

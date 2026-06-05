import { ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router-dom";

import { NAV_ITEMS, type NavItem } from "@/components/layout/nav-items";

function findTrail(pathname: string, items: NavItem[]): NavItem[] {
  for (const item of items) {
    if (item.to === pathname) return [item];
    if (item.children) {
      const child = findTrail(pathname, item.children);
      if (child.length) return [item, ...child];
    }
    if (item.to !== "/" && pathname.startsWith(item.to + "/") && item.children) {
      const child = findTrail(pathname, item.children);
      if (child.length) return [item, ...child];
    }
  }
  return [];
}

export function Breadcrumb() {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const trail = findTrail(pathname, NAV_ITEMS);

  if (trail.length === 0) return null;

  return (
    <nav className="flex items-center text-sm text-muted-foreground" aria-label="breadcrumb">
      <Link to="/" className="hover:text-foreground">
        {t("modules.dashboard")}
      </Link>
      {trail.map((item, i) => {
        const isLast = i === trail.length - 1;
        return (
          <span key={item.to} className="flex items-center">
            <ChevronRight className="mx-1 h-3 w-3" />
            {isLast ? (
              <span className="font-medium text-foreground">
                {t(item.i18nKey)}
              </span>
            ) : (
              <Link to={item.to} className="hover:text-foreground">
                {t(item.i18nKey)}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}

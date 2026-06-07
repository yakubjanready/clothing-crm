import type { LucideIcon } from "lucide-react";
import {
  Banknote,
  Bell,
  Building2,
  ClipboardList,
  Coins,
  LayoutDashboard,
  Package,
  ScrollText,
  ShoppingCart,
  Truck,
  Users,
  Warehouse,
} from "lucide-react";

export interface NavItem {
  to: string;
  i18nKey: string; // modules.<key>
  icon: LucideIcon;
  /** Item ko'rinishi uchun kerakli permission code'lar. Bo'sh yoki yo'q bo'lsa — hammaga ochiq. */
  requires?: readonly string[];
  children?: NavItem[];
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", i18nKey: "modules.dashboard", icon: LayoutDashboard },
  {
    to: "/hr",
    i18nKey: "modules.hr",
    icon: Users,
    requires: ["hr:read"],
    children: [
      {
        to: "/hr/departments",
        i18nKey: "modules.hr_departments",
        icon: Building2,
        requires: ["hr:read"],
      },
      {
        to: "/hr/positions",
        i18nKey: "modules.hr_positions",
        icon: ClipboardList,
        requires: ["hr:read"],
      },
      {
        to: "/hr/employees",
        i18nKey: "modules.hr_employees",
        icon: Users,
        requires: ["hr:read"],
      },
    ],
  },
  {
    to: "/catalog",
    i18nKey: "modules.catalog",
    icon: Package,
    requires: ["product:read"],
    children: [
      {
        to: "/catalog/categories",
        i18nKey: "modules.catalog_categories",
        icon: Package,
        requires: ["product:read"],
      },
      {
        to: "/catalog/brands",
        i18nKey: "modules.catalog_brands",
        icon: Package,
        requires: ["product:read"],
      },
      {
        to: "/catalog/products",
        i18nKey: "modules.catalog_products",
        icon: Package,
        requires: ["product:read"],
      },
    ],
  },
  {
    to: "/warehouse",
    i18nKey: "modules.warehouse",
    icon: Warehouse,
    requires: ["warehouse:read"],
    children: [
      {
        to: "/warehouse/warehouses",
        i18nKey: "modules.warehouse_warehouses",
        icon: Warehouse,
        requires: ["warehouse:read"],
      },
      {
        to: "/warehouse/stock",
        i18nKey: "modules.warehouse_stock",
        icon: Warehouse,
        requires: ["warehouse:read"],
      },
      {
        to: "/warehouse/movements",
        i18nKey: "modules.warehouse_movements",
        icon: Warehouse,
        requires: ["warehouse:read"],
      },
      {
        to: "/warehouse/inventory",
        i18nKey: "modules.warehouse_inventory",
        icon: Warehouse,
        requires: ["warehouse:read"],
      },
    ],
  },
  { to: "/customers", i18nKey: "modules.customers", icon: Users, requires: ["customer:read"] },
  {
    to: "/sales",
    i18nKey: "modules.sales",
    icon: ShoppingCart,
    requires: ["order:read"],
    children: [
      {
        to: "/sales/orders",
        i18nKey: "modules.sales_orders",
        icon: ShoppingCart,
        requires: ["order:read"],
      },
      {
        to: "/sales/invoices",
        i18nKey: "modules.sales_invoices",
        icon: ScrollText,
        requires: ["order:read"],
      },
      {
        to: "/sales/returns",
        i18nKey: "modules.sales_returns",
        icon: ShoppingCart,
        requires: ["order:read"],
      },
    ],
  },
  {
    to: "/procurement",
    i18nKey: "modules.procurement",
    icon: Truck,
    requires: ["purchase:read"],
    children: [
      {
        to: "/procurement/suppliers",
        i18nKey: "modules.procurement_suppliers",
        icon: Truck,
        requires: ["purchase:read"],
      },
      {
        to: "/procurement/purchases",
        i18nKey: "modules.procurement_purchases",
        icon: Truck,
        requires: ["purchase:read"],
      },
    ],
  },
  {
    to: "/finance",
    i18nKey: "modules.finance",
    icon: Coins,
    requires: ["accounting:read"],
    children: [
      {
        to: "/finance/accounts",
        i18nKey: "modules.finance_accounts",
        icon: Banknote,
        requires: ["accounting:read"],
      },
      {
        to: "/finance/payments",
        i18nKey: "modules.finance_payments",
        icon: Coins,
        requires: ["accounting:read"],
      },
      {
        to: "/finance/debts",
        i18nKey: "modules.finance_debts",
        icon: Coins,
        requires: ["accounting:read"],
      },
    ],
  },
  { to: "/notifications", i18nKey: "modules.notifications", icon: Bell },
  { to: "/audit", i18nKey: "modules.audit", icon: ScrollText, requires: ["audit:read"] },
  { to: "/users", i18nKey: "modules.users", icon: Users, requires: ["user:read"] },
];

/** Item ko'rinishi tekshiruvi: requires bo'sh bo'lsa — true; aks holda kamida bitta permission mos kelsa true. */
export function navItemAllowed(item: NavItem, perms: ReadonlySet<string>): boolean {
  if (!item.requires || item.requires.length === 0) return true;
  return item.requires.some((p) => perms.has(p));
}

/** Daraxtni permission'lar bo'yicha filterlash. Parent ko'rinmaydi, agar bola hech qaysi bola ham ko'rinmasa. */
export function filterNav(items: readonly NavItem[], perms: ReadonlySet<string>): NavItem[] {
  const result: NavItem[] = [];
  for (const item of items) {
    if (!navItemAllowed(item, perms)) continue;
    if (item.children && item.children.length > 0) {
      const visibleChildren = filterNav(item.children, perms);
      if (visibleChildren.length === 0) continue;
      result.push({ ...item, children: visibleChildren });
    } else {
      result.push(item);
    }
  }
  return result;
}

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
  i18nKey: string;       // modules.<key>
  icon: LucideIcon;
  children?: NavItem[];
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", i18nKey: "modules.dashboard", icon: LayoutDashboard },
  {
    to: "/hr",
    i18nKey: "modules.hr",
    icon: Users,
    children: [
      { to: "/hr/departments", i18nKey: "modules.hr_departments", icon: Building2 },
      { to: "/hr/positions",   i18nKey: "modules.hr_positions",   icon: ClipboardList },
      { to: "/hr/employees",   i18nKey: "modules.hr_employees",   icon: Users },
    ],
  },
  {
    to: "/catalog",
    i18nKey: "modules.catalog",
    icon: Package,
    children: [
      { to: "/catalog/categories", i18nKey: "modules.catalog_categories", icon: Package },
      { to: "/catalog/brands",     i18nKey: "modules.catalog_brands",     icon: Package },
      { to: "/catalog/products",   i18nKey: "modules.catalog_products",   icon: Package },
    ],
  },
  {
    to: "/warehouse",
    i18nKey: "modules.warehouse",
    icon: Warehouse,
    children: [
      { to: "/warehouse/warehouses", i18nKey: "modules.warehouse_warehouses", icon: Warehouse },
      { to: "/warehouse/stock",      i18nKey: "modules.warehouse_stock",      icon: Warehouse },
      { to: "/warehouse/movements",  i18nKey: "modules.warehouse_movements",  icon: Warehouse },
      { to: "/warehouse/inventory",  i18nKey: "modules.warehouse_inventory",  icon: Warehouse },
    ],
  },
  { to: "/customers", i18nKey: "modules.customers", icon: Users },
  {
    to: "/sales",
    i18nKey: "modules.sales",
    icon: ShoppingCart,
    children: [
      { to: "/sales/orders",   i18nKey: "modules.sales_orders",   icon: ShoppingCart },
      { to: "/sales/invoices", i18nKey: "modules.sales_invoices", icon: ScrollText },
      { to: "/sales/returns",  i18nKey: "modules.sales_returns",  icon: ShoppingCart },
    ],
  },
  {
    to: "/procurement",
    i18nKey: "modules.procurement",
    icon: Truck,
    children: [
      { to: "/procurement/suppliers", i18nKey: "modules.procurement_suppliers", icon: Truck },
      { to: "/procurement/purchases", i18nKey: "modules.procurement_purchases", icon: Truck },
    ],
  },
  {
    to: "/finance",
    i18nKey: "modules.finance",
    icon: Coins,
    children: [
      { to: "/finance/accounts", i18nKey: "modules.finance_accounts", icon: Banknote },
      { to: "/finance/payments", i18nKey: "modules.finance_payments", icon: Coins },
      { to: "/finance/debts",    i18nKey: "modules.finance_debts",    icon: Coins },
    ],
  },
  { to: "/notifications", i18nKey: "modules.notifications", icon: Bell },
  { to: "/audit",         i18nKey: "modules.audit",         icon: ScrollText },
  { to: "/users",         i18nKey: "modules.users",         icon: Users },
];

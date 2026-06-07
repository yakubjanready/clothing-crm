import { Warehouse } from "lucide-react";
import { describe, expect, it } from "vitest";

import { filterNav, navItemAllowed, type NavItem } from "./nav-items";

const ROOT: NavItem[] = [
  { to: "/", i18nKey: "modules.dashboard", icon: Warehouse },
  {
    to: "/warehouse",
    i18nKey: "modules.warehouse",
    icon: Warehouse,
    requires: ["warehouse:read"],
    children: [
      {
        to: "/warehouse/stock",
        i18nKey: "modules.warehouse_stock",
        icon: Warehouse,
        requires: ["warehouse:read"],
      },
    ],
  },
  {
    to: "/hr",
    i18nKey: "modules.hr",
    icon: Warehouse,
    requires: ["hr:read"],
    children: [
      {
        to: "/hr/employees",
        i18nKey: "modules.hr_employees",
        icon: Warehouse,
        requires: ["hr:read"],
      },
    ],
  },
];

describe("navItemAllowed", () => {
  it("opens items with no requires for everyone", () => {
    expect(navItemAllowed(ROOT[0], new Set())).toBe(true);
  });

  it("denies when required permission missing", () => {
    expect(navItemAllowed(ROOT[1], new Set())).toBe(false);
  });

  it("opens when at least one required permission present", () => {
    expect(navItemAllowed(ROOT[1], new Set(["warehouse:read"]))).toBe(true);
  });
});

describe("filterNav", () => {
  it("warehouse-only user sees Dashboard + Warehouse, not HR", () => {
    const result = filterNav(ROOT, new Set(["warehouse:read"]));
    const tos = result.map((i) => i.to);
    expect(tos).toEqual(["/", "/warehouse"]);
    expect(result[1].children?.map((c) => c.to)).toEqual(["/warehouse/stock"]);
  });

  it("hr-only user sees Dashboard + HR, not Warehouse", () => {
    const result = filterNav(ROOT, new Set(["hr:read"]));
    const tos = result.map((i) => i.to);
    expect(tos).toEqual(["/", "/hr"]);
  });

  it("admin with both perms sees everything", () => {
    const result = filterNav(ROOT, new Set(["warehouse:read", "hr:read"]));
    expect(result.map((i) => i.to)).toEqual(["/", "/warehouse", "/hr"]);
  });

  it("no perms — only requirement-less items remain", () => {
    const result = filterNav(ROOT, new Set());
    expect(result.map((i) => i.to)).toEqual(["/"]);
  });

  it("hides parent group whose children are all denied", () => {
    const tree: NavItem[] = [
      {
        to: "/x",
        i18nKey: "x",
        icon: Warehouse,
        children: [{ to: "/x/a", i18nKey: "x.a", icon: Warehouse, requires: ["nonexistent"] }],
      },
    ];
    expect(filterNav(tree, new Set()).length).toBe(0);
  });
});

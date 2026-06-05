import { describe, expect, it } from "vitest";

import { productSchema } from "./product-schema";

describe("productSchema (Zod)", () => {
  const validBase = {
    name: "Mayka",
    gender: "men",
    category_id: "00000000-0000-0000-0000-000000000001",
    is_active: true,
    description: "",
    material: "",
    brand_id: "",
  };

  it("accepts a valid product", () => {
    const r = productSchema.safeParse(validBase);
    expect(r.success).toBe(true);
  });

  it("rejects empty name", () => {
    const r = productSchema.safeParse({ ...validBase, name: "" });
    expect(r.success).toBe(false);
    if (!r.success) {
      expect(r.error.issues.some((i) => i.path[0] === "name")).toBe(true);
    }
  });

  it("rejects unknown gender", () => {
    const r = productSchema.safeParse({ ...validBase, gender: "alien" });
    expect(r.success).toBe(false);
  });

  it("rejects non-uuid category_id", () => {
    const r = productSchema.safeParse({ ...validBase, category_id: "not-a-uuid" });
    expect(r.success).toBe(false);
  });

  it("accepts empty brand_id (optional)", () => {
    const r = productSchema.safeParse({ ...validBase, brand_id: "" });
    expect(r.success).toBe(true);
  });
});

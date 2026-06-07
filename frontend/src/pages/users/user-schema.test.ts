import { describe, expect, it } from "vitest";

import {
  passwordResetSchema,
  userCreateSchema,
  userEditSchema,
} from "./user-schema";

const VALID_UUID = "00000000-0000-0000-0000-000000000001";

describe("userCreateSchema", () => {
  const valid = {
    email: "user@example.com",
    full_name: "Jasur Karimov",
    password: "Secret12!",
    role_ids: [VALID_UUID],
  };

  it("accepts a valid payload", () => {
    expect(userCreateSchema.safeParse(valid).success).toBe(true);
  });

  it("rejects invalid email", () => {
    const r = userCreateSchema.safeParse({ ...valid, email: "not-email" });
    expect(r.success).toBe(false);
    if (!r.success) expect(r.error.issues.some((i) => i.path[0] === "email")).toBe(true);
  });

  it("rejects password shorter than 8 chars", () => {
    const r = userCreateSchema.safeParse({ ...valid, password: "short" });
    expect(r.success).toBe(false);
    if (!r.success) expect(r.error.issues.some((i) => i.path[0] === "password")).toBe(true);
  });

  it("rejects empty full_name", () => {
    const r = userCreateSchema.safeParse({ ...valid, full_name: "" });
    expect(r.success).toBe(false);
  });

  it("defaults role_ids to empty array when omitted", () => {
    const r = userCreateSchema.safeParse({
      email: valid.email,
      full_name: valid.full_name,
      password: valid.password,
    });
    expect(r.success).toBe(true);
    if (r.success) expect(r.data.role_ids).toEqual([]);
  });

  it("rejects non-uuid role_id", () => {
    const r = userCreateSchema.safeParse({ ...valid, role_ids: ["nope"] });
    expect(r.success).toBe(false);
  });
});

describe("userEditSchema", () => {
  it("accepts a valid edit payload", () => {
    const r = userEditSchema.safeParse({
      full_name: "Updated Name",
      is_active: false,
      role_ids: [],
    });
    expect(r.success).toBe(true);
  });

  it("requires is_active boolean", () => {
    const r = userEditSchema.safeParse({
      full_name: "X",
      is_active: "yes",
      role_ids: [],
    });
    expect(r.success).toBe(false);
  });
});

describe("passwordResetSchema", () => {
  it("accepts password >= 8 chars", () => {
    expect(passwordResetSchema.safeParse({ password: "longenough" }).success).toBe(true);
  });

  it("rejects password < 8 chars", () => {
    expect(passwordResetSchema.safeParse({ password: "7chars!" }).success).toBe(false);
  });
});

import { z } from "zod";

export const userCreateSchema = z.object({
  email: z.string().email("To'g'ri email kiriting").max(255),
  full_name: z.string().min(1, "Majburiy").max(255),
  password: z.string().min(8, "Kamida 8 belgi").max(128),
  role_ids: z.array(z.string().uuid()).default([]),
});

export type UserCreateFormValues = z.infer<typeof userCreateSchema>;

export const userEditSchema = z.object({
  full_name: z.string().min(1, "Majburiy").max(255),
  is_active: z.boolean(),
  role_ids: z.array(z.string().uuid()).default([]),
});

export type UserEditFormValues = z.infer<typeof userEditSchema>;

export const passwordResetSchema = z.object({
  password: z.string().min(8, "Kamida 8 belgi").max(128),
});

export type PasswordResetFormValues = z.infer<typeof passwordResetSchema>;

export const DEFAULT_USER_CREATE: UserCreateFormValues = {
  email: "",
  full_name: "",
  password: "",
  role_ids: [],
};

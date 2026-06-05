import { z } from "zod";

export const GENDERS = ["men", "women", "unisex", "kids", "boys", "girls"] as const;

export const productSchema = z.object({
  name: z.string().min(1, "Majburiy").max(255),
  description: z.string().max(2000).optional().or(z.literal("")),
  material: z.string().max(128).optional().or(z.literal("")),
  gender: z.enum(GENDERS),
  category_id: z.string().uuid("Kategoriya tanlang"),
  brand_id: z.string().uuid().optional().or(z.literal("")),
  is_active: z.boolean(),
});

export type ProductFormValues = z.infer<typeof productSchema>;

export const DEFAULT_PRODUCT: ProductFormValues = {
  name: "",
  description: "",
  material: "",
  gender: "unisex",
  category_id: "",
  brand_id: "",
  is_active: true,
};

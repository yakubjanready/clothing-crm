export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export type Gender = "men" | "women" | "unisex" | "kids" | "boys" | "girls";

export interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  parent_id?: string | null;
}

export interface Brand {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  country?: string | null;
  logo_url?: string | null;
}

export interface Product {
  id: string;
  name: string;
  slug: string;
  sku_prefix: string;
  description?: string | null;
  material?: string | null;
  gender: Gender;
  images: string[];
  is_active: boolean;
  category_id: string;
  brand_id?: string | null;
}

export interface ProductVariant {
  id: string;
  product_id: string;
  sku: string;
  size: string;
  color: string;
  color_hex?: string | null;
  wholesale_price: string;
  retail_price: string;
  barcode?: string | null;
  image_url?: string | null;
  is_active: boolean;
}

export interface VariantColorSpec {
  name: string;
  hex?: string | null;
}

export interface VariantMatrixRequest {
  sizes: string[];
  colors: VariantColorSpec[];
  wholesale_price: string;
  retail_price: string;
  is_active?: boolean;
}

export interface VariantMatrixResponse {
  created: ProductVariant[];
  skipped_existing: { size: string; color: string }[];
}

export interface ImageUploadResponse {
  url: string;
  filename: string;
  content_type: string;
  size_bytes: number;
}

import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  Page,
  Product,
  ProductVariant,
  VariantMatrixRequest,
  VariantMatrixResponse,
  ImageUploadResponse,
  Gender,
} from "./types";

// ---- Query keys ----
export const productKeys = {
  all: ["products"] as const,
  list: (params: ProductsListParams) => ["products", "list", params] as const,
  detail: (id: string) => ["products", "detail", id] as const,
  variants: (id: string) => ["products", id, "variants"] as const,
};

export interface ProductsListParams {
  page?: number;
  page_size?: number;
  search?: string;
  gender?: Gender;
  category_id?: string;
  brand_id?: string;
  is_active?: boolean;
}

// ---- Hooks ----

export function useProductsList(params: ProductsListParams): UseQueryResult<Page<Product>> {
  return useQuery({
    queryKey: productKeys.list(params),
    queryFn: async () => {
      const r = await api.get<Page<Product>>("/products", { params });
      return r.data;
    },
  });
}

export function useProduct(id: string | undefined) {
  return useQuery({
    queryKey: productKeys.detail(id ?? ""),
    enabled: !!id,
    queryFn: async () => {
      const r = await api.get<Product>(`/products/${id}`);
      return r.data;
    },
  });
}

export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<Product>) => {
      const r = await api.post<Product>("/products", body);
      return r.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: productKeys.all });
    },
  });
}

export function useUpdateProduct(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<Product>) => {
      const r = await api.patch<Product>(`/products/${id}`, body);
      return r.data;
    },
    onSuccess: (data) => {
      qc.setQueryData(productKeys.detail(id), data);
      void qc.invalidateQueries({ queryKey: productKeys.all });
    },
  });
}

export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/products/${id}`);
      return id;
    },
    // ---- Optimistik: ro'yxatdan darhol olib tashlash ----
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: productKeys.all });
      const snapshots = qc.getQueriesData<Page<Product>>({
        queryKey: ["products", "list"],
      });
      snapshots.forEach(([key, data]) => {
        if (!data) return;
        qc.setQueryData<Page<Product>>(key, {
          ...data,
          items: data.items.filter((p) => p.id !== id),
          total: Math.max(0, data.total - 1),
        });
      });
      return { snapshots };
    },
    onError: (_e, _id, ctx) => {
      ctx?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: productKeys.all });
    },
  });
}

// ---- Variants ----

export function useProductVariants(productId: string | undefined) {
  return useQuery({
    queryKey: productKeys.variants(productId ?? ""),
    enabled: !!productId,
    queryFn: async () => {
      const r = await api.get<ProductVariant[]>(`/products/${productId}/variants`);
      return r.data;
    },
  });
}

export function useCreateVariantMatrix(productId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: VariantMatrixRequest) => {
      const r = await api.post<VariantMatrixResponse>(
        `/products/${productId}/variants/matrix`,
        body,
      );
      return r.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: productKeys.variants(productId) });
    },
  });
}

// ---- Image upload ----

export function useUploadImage() {
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post<ImageUploadResponse>("/upload/image", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return r.data;
    },
  });
}

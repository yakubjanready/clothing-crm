import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Brand, Category, Page } from "./types";

// Selectlar uchun katta sahifa (kichik biznes uchun yetarli;
// keyin combobox+search bilan kengaytirish mumkin).
const SELECT_PAGE = 100;

export function useCategoriesList() {
  return useQuery({
    queryKey: ["categories", "select"],
    queryFn: async () => {
      const r = await api.get<Page<Category>>("/categories", {
        params: { page: 1, page_size: SELECT_PAGE },
      });
      return r.data.items;
    },
  });
}

export function useBrandsList() {
  return useQuery({
    queryKey: ["brands", "select"],
    queryFn: async () => {
      const r = await api.get<Page<Brand>>("/brands", {
        params: { page: 1, page_size: SELECT_PAGE },
      });
      return r.data.items;
    },
  });
}

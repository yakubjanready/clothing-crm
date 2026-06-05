import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { useBrandsList, useCategoriesList } from "@/api/catalog";
import type { Product } from "@/api/types";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  DEFAULT_PRODUCT,
  GENDERS,
  productSchema,
  type ProductFormValues,
} from "./product-schema";

const NO_BRAND = "__none__";

interface ProductFormProps {
  initial?: Product;
  onSubmit: (values: ProductFormValues) => Promise<void> | void;
  submitLabel: string;
  isSubmitting?: boolean;
}

export function ProductForm({
  initial,
  onSubmit,
  submitLabel,
  isSubmitting,
}: ProductFormProps) {
  const { t } = useTranslation();
  const categories = useCategoriesList();
  const brands = useBrandsList();

  const form = useForm<ProductFormValues>({
    resolver: zodResolver(productSchema),
    defaultValues: initial
      ? {
          name: initial.name,
          description: initial.description ?? "",
          material: initial.material ?? "",
          gender: initial.gender,
          category_id: initial.category_id,
          brand_id: initial.brand_id ?? "",
          is_active: initial.is_active,
        }
      : DEFAULT_PRODUCT,
  });

  useEffect(() => {
    if (initial) {
      form.reset({
        name: initial.name,
        description: initial.description ?? "",
        material: initial.material ?? "",
        gender: initial.gender,
        category_id: initial.category_id,
        brand_id: initial.brand_id ?? "",
        is_active: initial.is_active,
      });
    }
  }, [initial, form]);

  return (
    <Form {...form}>
      <form
        className="space-y-5"
        onSubmit={form.handleSubmit(async (v) => {
          // brand_id bo'sh string bo'lsa null'ga aylantirib backendga yuboramiz
          await onSubmit({
            ...v,
            brand_id: v.brand_id || undefined,
            description: v.description || undefined,
            material: v.material || undefined,
          } as ProductFormValues);
        })}
      >
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("products.fields.name")}</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid gap-4 md:grid-cols-2">
          <FormField
            control={form.control}
            name="gender"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("products.fields.gender")}</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {GENDERS.map((g) => (
                      <SelectItem key={g} value={g}>
                        {t(`products.gender.${g}`)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="material"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("products.fields.material")}</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <FormField
            control={form.control}
            name="category_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("products.fields.category")}</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="—" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {(categories.data ?? []).map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="brand_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("products.fields.brand")}</FormLabel>
                <Select
                  value={field.value || NO_BRAND}
                  onValueChange={(v) =>
                    field.onChange(v === NO_BRAND ? "" : v)
                  }
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="—" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value={NO_BRAND}>—</SelectItem>
                    {(brands.data ?? []).map((b) => (
                      <SelectItem key={b.id} value={b.id}>
                        {b.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("products.fields.description")}</FormLabel>
              <FormControl>
                <Textarea rows={4} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="is_active"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center gap-3 space-y-0">
              <FormControl>
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                  className="h-4 w-4"
                />
              </FormControl>
              <FormLabel>{t("products.fields.is_active")}</FormLabel>
            </FormItem>
          )}
        />

        <div className="flex justify-end gap-2 pt-2">
          <Button type="submit" disabled={isSubmitting}>
            {submitLabel}
          </Button>
        </div>
      </form>
    </Form>
  );
}

import { Plus, Trash2, Pencil, Eye } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { useBrandsList, useCategoriesList } from "@/api/catalog";
import { useDeleteProduct, useProductsList, type ProductsListParams } from "@/api/products";
import type { Gender, Product } from "@/api/types";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable, type Column } from "@/components/common/DataTable";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Pagination } from "@/components/common/Pagination";
import { PageHeader } from "@/components/common/PageHeader";
import { SearchInput } from "@/components/common/SearchInput";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const GENDERS: Gender[] = ["men", "women", "unisex", "kids", "boys", "girls"];
const ALL_VALUE = "__all__";

export function ProductsListPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [params, setParams] = useState<ProductsListParams>({
    page: 1,
    page_size: 10,
    is_active: true,
  });
  const [toDelete, setToDelete] = useState<Product | null>(null);

  const { data, isLoading, isError } = useProductsList(params);
  const categories = useCategoriesList();
  const brands = useBrandsList();
  const del = useDeleteProduct();

  function setFilter<K extends keyof ProductsListParams>(
    key: K,
    value: ProductsListParams[K] | undefined,
  ) {
    setParams((p) => ({ ...p, page: 1, [key]: value }));
  }

  const columns: Column<Product>[] = [
    {
      key: "images",
      header: "",
      className: "w-12",
      render: (p) =>
        p.images?.[0] ? (
          <img src={p.images[0]} alt="" className="h-9 w-9 rounded object-cover" />
        ) : (
          <div className="h-9 w-9 rounded bg-muted" />
        ),
    },
    { key: "sku_prefix", header: t("products.fields.sku_prefix"), className: "font-mono text-xs" },
    {
      key: "name",
      header: t("products.fields.name"),
      render: (p) => (
        <Link to={`/catalog/products/${p.id}`} className="font-medium hover:underline">
          {p.name}
        </Link>
      ),
    },
    {
      key: "gender",
      header: t("products.fields.gender"),
      render: (p) => <Badge variant="secondary">{t(`products.gender.${p.gender}`)}</Badge>,
    },
    {
      key: "is_active",
      header: t("products.fields.is_active"),
      render: (p) => (p.is_active ? <Badge>✓</Badge> : <Badge variant="outline">—</Badge>),
    },
    {
      key: "actions",
      header: t("common.actions"),
      className: "w-32 text-right",
      render: (p) => (
        <div className="flex justify-end gap-1">
          <Button size="icon" variant="ghost" asChild aria-label="view">
            <Link to={`/catalog/products/${p.id}`}>
              <Eye className="h-4 w-4" />
            </Link>
          </Button>
          <Button size="icon" variant="ghost" asChild aria-label="edit">
            <Link to={`/catalog/products/${p.id}/edit`}>
              <Pencil className="h-4 w-4" />
            </Link>
          </Button>
          <Button size="icon" variant="ghost" onClick={() => setToDelete(p)} aria-label="delete">
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title={t("products.list_title")}
        description={t("products.list_description")}
        actions={
          <Button onClick={() => navigate("/catalog/products/new")}>
            <Plus className="mr-2 h-4 w-4" />
            {t("products.new")}
          </Button>
        }
      />

      <Card className="mb-4">
        <CardContent className="grid gap-3 p-4 md:grid-cols-4">
          <SearchInput
            value={params.search ?? ""}
            onChange={(v) => setFilter("search", v || undefined)}
            placeholder={t("common.search")}
          />
          <Select
            value={params.gender ?? ALL_VALUE}
            onValueChange={(v) => setFilter("gender", v === ALL_VALUE ? undefined : (v as Gender))}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("products.filter_gender")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_VALUE}>{t("products.all")}</SelectItem>
              {GENDERS.map((g) => (
                <SelectItem key={g} value={g}>
                  {t(`products.gender.${g}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={params.category_id ?? ALL_VALUE}
            onValueChange={(v) => setFilter("category_id", v === ALL_VALUE ? undefined : v)}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("products.filter_category")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_VALUE}>{t("products.all")}</SelectItem>
              {(categories.data ?? []).map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={params.brand_id ?? ALL_VALUE}
            onValueChange={(v) => setFilter("brand_id", v === ALL_VALUE ? undefined : v)}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("products.filter_brand")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_VALUE}>{t("products.all")}</SelectItem>
              {(brands.data ?? []).map((b) => (
                <SelectItem key={b.id} value={b.id}>
                  {b.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingSpinner />
      ) : isError ? (
        <Card className="p-8 text-center text-sm text-destructive">{t("common.error")}</Card>
      ) : (
        <>
          <DataTable
            columns={columns}
            rows={data?.items ?? []}
            rowKey={(p) => p.id}
            emptyTitle={t("common.no_data")}
          />
          {data && data.total > 0 && (
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              pageSize={data.page_size}
              onPageChange={(p) => setParams((s) => ({ ...s, page: p }))}
            />
          )}
        </>
      )}

      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        title={t("products.delete_confirm_title")}
        description={toDelete ? `${toDelete.name} — ${t("products.delete_confirm_desc")}` : ""}
        destructive
        onConfirm={async () => {
          if (!toDelete) return;
          try {
            await del.mutateAsync(toDelete.id);
            toast.success(t("products.deleted_toast"));
          } catch {
            toast.error(t("products.error_toast"));
          }
        }}
      />
    </div>
  );
}

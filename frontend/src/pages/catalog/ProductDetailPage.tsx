import { ArrowLeft, Pencil, Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { useProduct, useProductVariants, useUpdateProduct } from "@/api/products";
import { DataTable, type Column } from "@/components/common/DataTable";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { PageHeader } from "@/components/common/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

import { ImageDropzone } from "./ImageDropzone";
import { VariantMatrixDialog } from "./VariantMatrixDialog";

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const { data, isLoading } = useProduct(id);
  const variants = useProductVariants(id);
  const update = useUpdateProduct(id ?? "");
  const [matrixOpen, setMatrixOpen] = useState(false);

  if (isLoading || !data) return <LoadingSpinner />;

  async function saveImages(urls: string[]) {
    try {
      await update.mutateAsync({ images: urls });
      toast.success(t("products.updated_toast"));
    } catch {
      toast.error(t("products.error_toast"));
    }
  }

  const variantColumns: Column<NonNullable<typeof variants.data>[number]>[] = [
    { key: "sku", header: t("variants.sku"), className: "font-mono text-xs" },
    { key: "size", header: t("variants.size") },
    {
      key: "color",
      header: t("variants.color"),
      render: (v) => (
        <div className="flex items-center gap-2">
          {v.color_hex && (
            <span
              className="inline-block h-3 w-3 rounded-full border"
              style={{ backgroundColor: v.color_hex }}
            />
          )}
          {v.color}
        </div>
      ),
    },
    { key: "wholesale_price", header: t("variants.wholesale") },
    { key: "retail_price", header: t("variants.retail") },
    {
      key: "is_active",
      header: t("products.fields.is_active"),
      render: (v) => (v.is_active ? <Badge>✓</Badge> : <Badge variant="outline">—</Badge>),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title={data.name}
        description={`${data.sku_prefix} · ${t(`products.gender.${data.gender}`)}`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link to="/catalog/products">
                <ArrowLeft className="mr-2 h-4 w-4" />
                {t("common.back")}
              </Link>
            </Button>
            <Button asChild>
              <Link to={`/catalog/products/${data.id}/edit`}>
                <Pencil className="mr-2 h-4 w-4" />
                {t("products.edit")}
              </Link>
            </Button>
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>{t("products.fields.images")}</CardTitle>
          </CardHeader>
          <CardContent>
            <ImageDropzone value={data.images ?? []} onChange={saveImages} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("products.detail")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label={t("products.fields.sku_prefix")} value={data.sku_prefix} mono />
            <Row label={t("products.fields.slug")} value={data.slug} mono />
            <Row label={t("products.fields.gender")} value={t(`products.gender.${data.gender}`)} />
            <Row label={t("products.fields.material")} value={data.material ?? "—"} />
            <Row label={t("products.fields.is_active")} value={data.is_active ? "✓" : "—"} />
            {data.description && (
              <>
                <Separator />
                <p className="whitespace-pre-wrap text-muted-foreground">{data.description}</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle>{t("variants.title")}</CardTitle>
          <Button onClick={() => setMatrixOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t("variants.create_matrix")}
          </Button>
        </CardHeader>
        <CardContent>
          {variants.isLoading ? (
            <LoadingSpinner />
          ) : (
            <DataTable
              columns={variantColumns}
              rows={variants.data ?? []}
              rowKey={(v) => v.id}
              emptyTitle={t("common.no_data")}
            />
          )}
        </CardContent>
      </Card>

      <VariantMatrixDialog productId={data.id} open={matrixOpen} onOpenChange={setMatrixOpen} />
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className={mono ? "font-mono text-xs" : ""}>{value}</span>
    </div>
  );
}

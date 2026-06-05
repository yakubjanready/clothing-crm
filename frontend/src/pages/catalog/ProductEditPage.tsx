import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { useProduct, useUpdateProduct } from "@/api/products";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/card";

import { ProductForm } from "./ProductForm";

export function ProductEditPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, isLoading } = useProduct(id);
  const m = useUpdateProduct(id ?? "");

  if (isLoading || !data) return <LoadingSpinner />;

  return (
    <div>
      <PageHeader title={`${t("products.edit")} — ${data.name}`} />
      <Card>
        <CardContent className="pt-6">
          <ProductForm
            initial={data}
            submitLabel={t("common.save")}
            isSubmitting={m.isPending}
            onSubmit={async (v) => {
              try {
                await m.mutateAsync(v);
                toast.success(t("products.updated_toast"));
                navigate(`/catalog/products/${id}`);
              } catch {
                toast.error(t("products.error_toast"));
              }
            }}
          />
        </CardContent>
      </Card>
    </div>
  );
}

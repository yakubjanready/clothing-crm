import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { useCreateProduct } from "@/api/products";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/card";

import { ProductForm } from "./ProductForm";

export function ProductCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const m = useCreateProduct();

  return (
    <div>
      <PageHeader title={t("products.new")} />
      <Card>
        <CardContent className="pt-6">
          <ProductForm
            submitLabel={t("common.save")}
            isSubmitting={m.isPending}
            onSubmit={async (v) => {
              try {
                const created = await m.mutateAsync(v);
                toast.success(t("products.created_toast"));
                navigate(`/catalog/products/${created.id}`, { replace: true });
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

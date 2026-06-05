import { useTranslation } from "react-i18next";

import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/stores/auth";

export function DashboardPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);

  return (
    <div>
      <PageHeader
        title={`${t("dashboard.welcome")}, ${user?.full_name ?? ""}`}
        description={t("dashboard.welcome_message")}
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { key: "modules.customers", value: "—" },
          { key: "modules.sales_orders", value: "—" },
          { key: "modules.warehouse_stock", value: "—" },
          { key: "modules.finance_debts", value: "—" },
        ].map((s) => (
          <Card key={s.key}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t(s.key)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">{s.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

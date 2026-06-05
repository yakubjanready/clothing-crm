import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <div className="grid min-h-screen place-items-center bg-muted/30 p-4">
      <div className="text-center">
        <h1 className="text-6xl font-bold">404</h1>
        <p className="mt-2 text-muted-foreground">Sahifa topilmadi</p>
        <Button asChild className="mt-6">
          <Link to="/">{t("modules.dashboard")}</Link>
        </Button>
      </div>
    </div>
  );
}

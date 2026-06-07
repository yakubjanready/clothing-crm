import { ShieldAlert } from "lucide-react";
import { useTranslation } from "react-i18next";

import { EmptyState } from "@/components/common/EmptyState";
import { useAuthStore } from "@/stores/auth";

interface PermissionGateProps {
  /** Kamida bittasi mavjud bo'lsa kirish ochiq. Bo'sh massiv — har doim ochiq. */
  anyOf?: readonly string[];
  children: React.ReactNode;
}

export function PermissionGate({ anyOf = [], children }: PermissionGateProps) {
  const { t } = useTranslation();
  const allowed = useAuthStore((s) => s.hasAnyPermission(anyOf));

  if (!allowed) {
    return (
      <EmptyState
        icon={<ShieldAlert className="h-10 w-10 text-destructive" />}
        title={t("common.forbidden_title")}
        description={t("common.forbidden_desc")}
      />
    );
  }
  return <>{children}</>;
}

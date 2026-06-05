import { Construction } from "lucide-react";
import { useTranslation } from "react-i18next";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";

interface PlaceholderPageProps {
  titleKey: string;
  descriptionKey?: string;
}

export function PlaceholderPage({ titleKey, descriptionKey }: PlaceholderPageProps) {
  const { t } = useTranslation();
  return (
    <div>
      <PageHeader
        title={t(titleKey)}
        description={descriptionKey ? t(descriptionKey) : undefined}
      />
      <EmptyState
        icon={<Construction className="h-10 w-10" />}
        title="Skelet"
        description={t(titleKey) + " — keyingi fazada to'liq amalga oshiriladi."}
      />
    </div>
  );
}

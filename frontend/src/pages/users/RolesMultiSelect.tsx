import { useTranslation } from "react-i18next";

import { useRolesList } from "@/api/users";
import { Badge } from "@/components/ui/badge";

interface RolesMultiSelectProps {
  value: string[];
  onChange: (next: string[]) => void;
  disabled?: boolean;
}

export function RolesMultiSelect({ value, onChange, disabled }: RolesMultiSelectProps) {
  const { t } = useTranslation();
  const { data: roles, isLoading } = useRolesList();

  function toggle(id: string) {
    if (disabled) return;
    onChange(value.includes(id) ? value.filter((x) => x !== id) : [...value, id]);
  }

  if (isLoading) return <div className="text-sm text-muted-foreground">{t("common.loading")}</div>;
  if (!roles || roles.length === 0)
    return <div className="text-sm text-muted-foreground">{t("users.no_roles")}</div>;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {roles.map((r) => {
          const checked = value.includes(r.id);
          return (
            <button
              key={r.id}
              type="button"
              onClick={() => toggle(r.id)}
              disabled={disabled}
              className={`rounded-full border px-3 py-1 text-xs transition ${
                checked
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-background text-muted-foreground hover:bg-muted"
              } ${disabled ? "opacity-60" : ""}`}
              aria-pressed={checked}
            >
              {r.name}
            </button>
          );
        })}
      </div>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1 text-xs">
          {roles
            .filter((r) => value.includes(r.id))
            .map((r) => (
              <Badge key={r.id} variant="secondary">
                {r.name}
              </Badge>
            ))}
        </div>
      )}
    </div>
  );
}

import { Pencil, Plus, RotateCcw, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import {
  useDeleteUser,
  useRestoreUser,
  useRolesList,
  useUsersList,
  type UsersListParams,
} from "@/api/users";
import type { AppUser } from "@/api/types";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable, type Column } from "@/components/common/DataTable";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { PageHeader } from "@/components/common/PageHeader";
import { Pagination } from "@/components/common/Pagination";
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

const ALL_VALUE = "__all__";
const ACTIVE_TRUE = "true";
const ACTIVE_FALSE = "false";

export function UsersListPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [params, setParams] = useState<UsersListParams>({ page: 1, page_size: 10 });
  const [toDelete, setToDelete] = useState<AppUser | null>(null);

  const { data, isLoading, isError } = useUsersList(params);
  const roles = useRolesList();
  const del = useDeleteUser();
  const restore = useRestoreUser();

  function setFilter<K extends keyof UsersListParams>(
    key: K,
    value: UsersListParams[K] | undefined,
  ) {
    setParams((p) => ({ ...p, page: 1, [key]: value }));
  }

  const columns: Column<AppUser>[] = [
    {
      key: "full_name",
      header: t("users.fields.full_name"),
      render: (u) => (
        <Link to={`/users/${u.id}`} className="font-medium hover:underline">
          {u.full_name}
        </Link>
      ),
    },
    { key: "email", header: t("users.fields.email"), className: "text-sm" },
    {
      key: "roles",
      header: t("users.fields.roles"),
      render: (u) =>
        u.roles.length === 0 ? (
          <span className="text-xs text-muted-foreground">—</span>
        ) : (
          <div className="flex flex-wrap gap-1">
            {u.roles.map((r) => (
              <Badge key={r.id} variant="secondary">
                {r.name}
              </Badge>
            ))}
          </div>
        ),
    },
    {
      key: "is_active",
      header: t("users.fields.is_active"),
      render: (u) =>
        u.is_active ? (
          <Badge>{t("common.yes")}</Badge>
        ) : (
          <Badge variant="outline">{t("common.no")}</Badge>
        ),
    },
    {
      key: "actions",
      header: t("common.actions"),
      className: "w-32 text-right",
      render: (u) => (
        <div className="flex justify-end gap-1">
          <Button size="icon" variant="ghost" asChild aria-label="edit">
            <Link to={`/users/${u.id}/edit`}>
              <Pencil className="h-4 w-4" />
            </Link>
          </Button>
          {u.is_active ? (
            <Button size="icon" variant="ghost" onClick={() => setToDelete(u)} aria-label="delete">
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          ) : (
            <Button
              size="icon"
              variant="ghost"
              onClick={async () => {
                try {
                  await restore.mutateAsync(u.id);
                  toast.success(t("users.restored_toast"));
                } catch {
                  toast.error(t("users.error_toast"));
                }
              }}
              aria-label="restore"
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title={t("users.list_title")}
        description={t("users.list_description")}
        actions={
          <Button onClick={() => navigate("/users/new")}>
            <Plus className="mr-2 h-4 w-4" />
            {t("users.new")}
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
            value={params.role_id ?? ALL_VALUE}
            onValueChange={(v) => setFilter("role_id", v === ALL_VALUE ? undefined : v)}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("users.filter_role")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_VALUE}>{t("common.all_roles")}</SelectItem>
              {(roles.data ?? []).map((r) => (
                <SelectItem key={r.id} value={r.id}>
                  {r.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={
              params.is_active === undefined
                ? ALL_VALUE
                : params.is_active
                  ? ACTIVE_TRUE
                  : ACTIVE_FALSE
            }
            onValueChange={(v) =>
              setFilter("is_active", v === ALL_VALUE ? undefined : v === ACTIVE_TRUE)
            }
          >
            <SelectTrigger>
              <SelectValue placeholder={t("users.filter_status")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_VALUE}>{t("common.all")}</SelectItem>
              <SelectItem value={ACTIVE_TRUE}>{t("users.active")}</SelectItem>
              <SelectItem value={ACTIVE_FALSE}>{t("users.inactive")}</SelectItem>
            </SelectContent>
          </Select>
          <Select
            value={params.include_deleted ? ACTIVE_TRUE : ACTIVE_FALSE}
            onValueChange={(v) => setFilter("include_deleted", v === ACTIVE_TRUE)}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("users.include_deleted")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ACTIVE_FALSE}>{t("users.exclude_deleted")}</SelectItem>
              <SelectItem value={ACTIVE_TRUE}>{t("users.include_deleted")}</SelectItem>
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
            rowKey={(u) => u.id}
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
        title={t("users.delete_confirm_title")}
        description={toDelete ? `${toDelete.full_name} — ${t("users.delete_confirm_desc")}` : ""}
        destructive
        onConfirm={async () => {
          if (!toDelete) return;
          try {
            await del.mutateAsync(toDelete.id);
            toast.success(t("users.deleted_toast"));
          } catch {
            toast.error(t("users.error_toast"));
          }
        }}
      />
    </div>
  );
}

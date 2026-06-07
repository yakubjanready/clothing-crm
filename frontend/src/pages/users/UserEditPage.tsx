import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { useResetPassword, useUpdateUser, useUser } from "@/api/users";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/stores/auth";

import { RolesMultiSelect } from "./RolesMultiSelect";
import {
  passwordResetSchema,
  userEditSchema,
  type PasswordResetFormValues,
  type UserEditFormValues,
} from "./user-schema";

export function UserEditPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const me = useAuthStore((s) => s.user);
  const { data, isLoading } = useUser(id);
  const update = useUpdateUser(id ?? "");
  const reset = useResetPassword(id ?? "");
  const [resetOpen, setResetOpen] = useState(false);

  const form = useForm<UserEditFormValues>({
    resolver: zodResolver(userEditSchema),
    defaultValues: { full_name: "", is_active: true, role_ids: [] },
  });

  const resetForm = useForm<PasswordResetFormValues>({
    resolver: zodResolver(passwordResetSchema),
    defaultValues: { password: "" },
  });

  useEffect(() => {
    if (data) {
      form.reset({
        full_name: data.full_name,
        is_active: data.is_active,
        role_ids: data.roles.map((r) => r.id),
      });
    }
  }, [data, form]);

  if (isLoading || !data) return <LoadingSpinner />;

  const isSelf = me?.id === data.id;

  return (
    <div>
      <PageHeader
        title={`${t("users.edit")} — ${data.full_name}`}
        actions={
          <Button variant="outline" onClick={() => setResetOpen(true)}>
            <KeyRound className="mr-2 h-4 w-4" />
            {t("users.reset_password")}
          </Button>
        }
      />

      <Card>
        <CardContent className="pt-6">
          <Form {...form}>
            <form
              className="space-y-5"
              onSubmit={form.handleSubmit(async (v) => {
                try {
                  // Backend o'zining rollarini o'zgartirishga ruxsat bermaydi —
                  // self bo'lsa role_ids'ni yubormaymiz.
                  const body = isSelf ? { full_name: v.full_name } : v;
                  await update.mutateAsync(body);
                  toast.success(t("users.updated_toast"));
                  navigate("/users");
                } catch {
                  toast.error(t("users.error_toast"));
                }
              })}
            >
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="full_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("users.fields.full_name")}</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormItem>
                  <FormLabel>{t("users.fields.email")}</FormLabel>
                  <Input value={data.email} disabled readOnly />
                </FormItem>
              </div>

              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center gap-3 space-y-0">
                    <FormControl>
                      <input
                        type="checkbox"
                        checked={field.value}
                        onChange={(e) => field.onChange(e.target.checked)}
                        disabled={isSelf}
                        className="h-4 w-4"
                      />
                    </FormControl>
                    <FormLabel>
                      {t("users.fields.is_active")}
                      {isSelf && (
                        <span className="ml-2 text-xs text-muted-foreground">
                          ({t("users.cannot_self_deactivate")})
                        </span>
                      )}
                    </FormLabel>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="role_ids"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("users.fields.roles")}</FormLabel>
                    <FormControl>
                      <RolesMultiSelect
                        value={field.value}
                        onChange={field.onChange}
                        disabled={isSelf}
                      />
                    </FormControl>
                    {isSelf && (
                      <p className="text-xs text-muted-foreground">
                        {t("users.cannot_self_role")}
                      </p>
                    )}
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => navigate("/users")}>
                  {t("common.cancel")}
                </Button>
                <Button type="submit" disabled={update.isPending}>
                  {t("common.save")}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Dialog open={resetOpen} onOpenChange={setResetOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("users.reset_password")}</DialogTitle>
            <DialogDescription>{t("users.reset_password_desc")}</DialogDescription>
          </DialogHeader>
          <Form {...resetForm}>
            <form
              id="reset-pw-form"
              onSubmit={resetForm.handleSubmit(async (v) => {
                try {
                  await reset.mutateAsync(v.password);
                  toast.success(t("users.password_reset_toast"));
                  resetForm.reset({ password: "" });
                  setResetOpen(false);
                } catch {
                  toast.error(t("users.error_toast"));
                }
              })}
              className="space-y-4"
            >
              <FormField
                control={resetForm.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("users.fields.new_password")}</FormLabel>
                    <FormControl>
                      <Input type="password" autoComplete="new-password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </form>
          </Form>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setResetOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button form="reset-pw-form" type="submit" disabled={reset.isPending}>
              {t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

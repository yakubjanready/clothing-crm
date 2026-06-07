import { zodResolver } from "@hookform/resolvers/zod";
import { isAxiosError } from "axios";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { useCreateUser } from "@/api/users";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";

import { RolesMultiSelect } from "./RolesMultiSelect";
import { DEFAULT_USER_CREATE, userCreateSchema, type UserCreateFormValues } from "./user-schema";

export function UserCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const m = useCreateUser();

  const form = useForm<UserCreateFormValues>({
    resolver: zodResolver(userCreateSchema),
    defaultValues: DEFAULT_USER_CREATE,
  });

  return (
    <div>
      <PageHeader title={t("users.new")} />
      <Card>
        <CardContent className="pt-6">
          <Form {...form}>
            <form
              className="space-y-5"
              onSubmit={form.handleSubmit(async (v) => {
                try {
                  await m.mutateAsync(v);
                  toast.success(t("users.created_toast"));
                  navigate("/users", { replace: true });
                } catch (e) {
                  if (isAxiosError(e) && e.response?.status === 409) {
                    form.setError("email", { message: t("users.email_taken") });
                  } else {
                    toast.error(t("users.error_toast"));
                  }
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
                        <Input autoComplete="name" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("users.fields.email")}</FormLabel>
                      <FormControl>
                        <Input type="email" autoComplete="email" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("users.fields.password")}</FormLabel>
                    <FormControl>
                      <Input type="password" autoComplete="new-password" {...field} />
                    </FormControl>
                    <FormMessage />
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
                      <RolesMultiSelect value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => navigate("/users")}>
                  {t("common.cancel")}
                </Button>
                <Button type="submit" disabled={m.isPending}>
                  {t("common.save")}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}

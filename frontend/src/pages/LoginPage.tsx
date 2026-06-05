import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { ThemeToggle } from "@/components/common/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { useAuthStore, useIsAuthenticated, type AuthUser } from "@/stores/auth";

interface LoginResp {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const isAuth = useIsAuthenticated();
  const login = useAuthStore((s) => s.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const m = useMutation({
    mutationFn: async (vars: { email: string; password: string }) => {
      const tokens = (
        await api.post<LoginResp>("/auth/login", vars)
      ).data;
      // Tokenlar oldindan o'rnatiladi, keyin /me ni chaqirish
      useAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token);
      const me = (await api.get<AuthUser>("/auth/me")).data;
      return { tokens, me };
    },
    onSuccess: ({ tokens, me }) => {
      login(tokens.access_token, tokens.refresh_token, me);
      const from =
        (location.state as { from?: { pathname: string } } | null)?.from
          ?.pathname ?? "/";
      navigate(from, { replace: true });
    },
  });

  if (isAuth) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="grid min-h-screen place-items-center bg-muted/30 p-4">
      <div className="absolute right-4 top-4 flex items-center gap-1">
        <LanguageSwitcher />
        <ThemeToggle />
      </div>
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-2">
          <CardTitle className="text-center text-xl">{t("auth.title")}</CardTitle>
          <CardDescription className="text-center">
            {t("auth.subtitle")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              m.mutate({ email, password });
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="email">{t("auth.email")}</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t("auth.password")}</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {m.isError && (
              <p className="text-sm text-destructive" role="alert">
                {t("auth.invalid_credentials")}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={m.isPending}>
              {m.isPending ? t("auth.logging_in") : t("auth.login")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

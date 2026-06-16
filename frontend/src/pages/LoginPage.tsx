import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { Sparkles } from "lucide-react";

import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { ThemeToggle } from "@/components/common/ThemeToggle";
import { Button } from "@/components/ui/button";
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
      const tokens = (await api.post<LoginResp>("/auth/login", vars)).data;
      // Tokenlar oldindan o'rnatiladi, keyin /me + permission'larni chaqirish
      useAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token);
      const [meResp, permsResp] = await Promise.all([
        api.get<AuthUser>("/auth/me"),
        api.get<string[]>("/users/me/permissions"),
      ]);
      return { tokens, me: meResp.data, permissions: permsResp.data };
    },
    onSuccess: ({ tokens, me, permissions }) => {
      login(tokens.access_token, tokens.refresh_token, me, permissions);
      const from =
        (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/";
      navigate(from, { replace: true });
    },
  });

  if (isAuth) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Chap — brend paneli (faqat lg+) */}
      <div className="relative hidden overflow-hidden bg-primary text-primary-foreground lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.5]"
          style={{
            backgroundImage:
              "radial-gradient(at 15% 20%, hsl(var(--gold) / 0.28) 0px, transparent 50%), radial-gradient(at 85% 90%, hsl(var(--gold) / 0.18) 0px, transparent 45%)",
          }}
        />
        <div className="relative flex items-center gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-xl bg-gold/95 text-gold-foreground shadow-gold">
            <span className="font-display text-lg font-semibold">UK</span>
          </div>
          <div>
            <div className="font-display text-xl font-semibold tracking-tight">Remodul CRM</div>
            <div className="text-xs uppercase tracking-[0.2em] text-primary-foreground/60">
              Kiyim-kechak
            </div>
          </div>
        </div>

        <div className="relative max-w-md space-y-6">
          <span className="inline-flex items-center gap-2 rounded-full border border-gold/40 bg-gold/10 px-3 py-1 text-xs font-medium text-gold">
            <Sparkles className="h-3.5 w-3.5" /> Premium remodul platforma
          </span>
          <h2 className="font-display text-4xl font-semibold leading-tight tracking-tight">
            Kiyim-kechak biznesingizni bitta joydan boshqaring.
          </h2>
          <p className="text-base leading-relaxed text-primary-foreground/70">
            Katalog, ombor, sotuvlar, mijozlar va moliya — barchasi nafis va tezkor
            interfeysda.
          </p>
        </div>

        <div className="relative flex items-center gap-6 text-sm text-primary-foreground/60">
          <span>Ombor</span>
          <span className="h-1 w-1 rounded-full bg-gold" />
          <span>Sotuvlar</span>
          <span className="h-1 w-1 rounded-full bg-gold" />
          <span>Moliya</span>
        </div>
      </div>

      {/* O'ng — forma */}
      <div className="relative grid place-items-center bg-grain p-6 sm:p-10">
        <div className="absolute right-4 top-4 flex items-center gap-1">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>

        <div className="w-full max-w-sm">
          {/* Mobil logotip */}
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-primary text-primary-foreground shadow-md ring-1 ring-gold/30">
              <span className="font-display text-base font-semibold">UK</span>
            </div>
            <div className="font-display text-lg font-semibold tracking-tight">
              Remodul <span className="text-gold">CRM</span>
            </div>
          </div>

          <div className="mb-8">
            <h1 className="font-display text-3xl font-semibold tracking-tight">
              {t("auth.title")}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">{t("auth.subtitle")}</p>
          </div>

          <form
            className="space-y-5"
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
              <p
                className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                role="alert"
              >
                {t("auth.invalid_credentials")}
              </p>
            )}
            <Button type="submit" size="lg" className="w-full" disabled={m.isPending}>
              {m.isPending ? t("auth.logging_in") : t("auth.login")}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}

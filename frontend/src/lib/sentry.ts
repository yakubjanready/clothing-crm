/**
 * Sentry init — agar VITE_SENTRY_DSN o'rnatilgan bo'lsa.
 * DSN bo'sh bo'lsa, hech narsa qilinmaydi (bundle hajmiga ta'siri yo'q —
 * @sentry/react tree-shake'lanmaydi, lekin runtime zero-cost bo'ladi).
 */
import * as Sentry from "@sentry/react";

export function initSentry(): boolean {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return false;

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
    integrations: [Sentry.browserTracingIntegration()],
  });
  return true;
}

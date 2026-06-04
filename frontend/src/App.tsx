import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { API_BASE_URL } from "@/lib/utils";

type HealthStatus = "idle" | "loading" | "ok" | "error";

interface HealthBody {
  status: string;
  app: string;
  env: string;
  version: string;
}

export default function App() {
  const [status, setStatus] = useState<HealthStatus>("idle");
  const [body, setBody] = useState<HealthBody | null>(null);

  async function pingHealth() {
    setStatus("loading");
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (!res.ok) throw new Error(String(res.status));
      setBody((await res.json()) as HealthBody);
      setStatus("ok");
    } catch {
      setStatus("error");
    }
  }

  useEffect(() => {
    void pingHealth();
  }, []);

  return (
    <main className="container mx-auto max-w-2xl py-16">
      <h1 className="text-3xl font-bold tracking-tight">
        Ulgurji Kiyim-kechak CRM
      </h1>
      <p className="mt-2 text-muted-foreground">
        Faza 1 — skelet. Backend bilan ulanish tekshiruvi.
      </p>

      <section className="mt-8 rounded-lg border p-6">
        <div className="flex items-center justify-between">
          <span className="font-medium">Backend /health</span>
          <span
            data-testid="health-status"
            className="rounded-md bg-muted px-3 py-1 text-sm"
          >
            {status}
          </span>
        </div>
        {body && (
          <pre className="mt-4 overflow-x-auto rounded-md bg-muted p-4 text-xs">
            {JSON.stringify(body, null, 2)}
          </pre>
        )}
        <Button className="mt-4" onClick={pingHealth}>
          Qayta tekshirish
        </Button>
      </section>
    </main>
  );
}

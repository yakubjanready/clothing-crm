import { useState } from "react";

import {
  useCustomersList,
  type Customer,
  type CustomerSegment,
  type CustomersListParams,
  type PriceType,
} from "@/api/customers";
import { DataTable, type Column } from "@/components/common/DataTable";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { PageHeader } from "@/components/common/PageHeader";
import { Pagination } from "@/components/common/Pagination";
import { SearchInput } from "@/components/common/SearchInput";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatMoney } from "@/lib/format";

const ALL = "__all__";

const SEGMENT: Record<
  CustomerSegment,
  { label: string; variant: "default" | "secondary" | "outline" | "destructive" }
> = {
  vip: { label: "VIP", variant: "default" },
  regular: { label: "Doimiy", variant: "secondary" },
  new: { label: "Yangi", variant: "outline" },
  inactive: { label: "Nofaol", variant: "destructive" },
};

const SEGMENT_KEYS = Object.keys(SEGMENT) as CustomerSegment[];

const PRICE_TYPE: Record<PriceType, string> = {
  wholesale: "Remodul",
  retail: "Chakana",
  special: "Maxsus",
};

export function CustomersListPage() {
  const [params, setParams] = useState<CustomersListParams>({ page: 1, page_size: 10 });

  const { data, isLoading, isError } = useCustomersList(params);

  function setFilter<K extends keyof CustomersListParams>(
    key: K,
    value: CustomersListParams[K] | undefined,
  ) {
    setParams((p) => ({ ...p, page: 1, [key]: value }));
  }

  const columns: Column<Customer>[] = [
    {
      key: "name",
      header: "Nomi",
      render: (c) => <span className="font-medium">{c.name}</span>,
    },
    {
      key: "segment",
      header: "Segment",
      render: (c) => <Badge variant={SEGMENT[c.segment].variant}>{SEGMENT[c.segment].label}</Badge>,
    },
    {
      key: "price_type",
      header: "Narx turi",
      render: (c) => PRICE_TYPE[c.price_type],
    },
    {
      key: "phone",
      header: "Telefon",
      render: (c) => c.phone ?? "—",
    },
    {
      key: "credit_limit",
      header: "Kredit limiti",
      className: "text-right",
      render: (c) => formatMoney(c.credit_limit),
    },
    {
      key: "current_debt",
      header: "Qarz",
      className: "text-right",
      render: (c) =>
        Number(c.current_debt) > 0 ? (
          <span className="text-destructive">{formatMoney(c.current_debt)}</span>
        ) : (
          formatMoney(c.current_debt)
        ),
    },
    {
      key: "is_active",
      header: "Holat",
      render: (c) => (
        <Badge variant={c.is_active ? "secondary" : "destructive"}>
          {c.is_active ? "Faol" : "Nofaol"}
        </Badge>
      ),
    },
  ];

  return (
    <div>
      <PageHeader title="Mijozlar" description="Mijozlar bazasi, segment va qarz holati" />

      <Card className="mb-4">
        <CardContent className="grid gap-3 p-4 md:grid-cols-3">
          <SearchInput
            value={params.search ?? ""}
            onChange={(v) => setFilter("search", v || undefined)}
            placeholder="Nomi bo'yicha qidirish"
          />
          <Select
            value={params.segment ?? ALL}
            onValueChange={(v) =>
              setFilter("segment", v === ALL ? undefined : (v as CustomerSegment))
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Segment" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Barcha</SelectItem>
              {SEGMENT_KEYS.map((s) => (
                <SelectItem key={s} value={s}>
                  {SEGMENT[s].label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={params.has_debt ? "yes" : ALL}
            onValueChange={(v) => setFilter("has_debt", v === ALL ? undefined : true)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Qarz holati" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Hammasi</SelectItem>
              <SelectItem value="yes">Qarzi borlar</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingSpinner />
      ) : isError ? (
        <Card className="p-8 text-center text-sm text-destructive">Xatolik yuz berdi</Card>
      ) : (
        <>
          <DataTable
            columns={columns}
            rows={data?.items ?? []}
            rowKey={(c) => c.id}
            emptyTitle="Mijoz yo'q"
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
    </div>
  );
}

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { AppLayout } from "@/components/layout/AppLayout";
import { ThemeProvider } from "@/components/theme-provider";
import "@/lib/i18n";
import { ProductCreatePage } from "@/pages/catalog/ProductCreatePage";
import { ProductDetailPage } from "@/pages/catalog/ProductDetailPage";
import { ProductEditPage } from "@/pages/catalog/ProductEditPage";
import { ProductsListPage } from "@/pages/catalog/ProductsListPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { PlaceholderPage } from "@/pages/PlaceholderPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Yangi modul to'liq amalga oshirilganda PlaceholderPage o'rniga
// haqiqiy pagelar import qilinadi.
const ph = (key: string) => <PlaceholderPage titleKey={key} />;

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/" element={<DashboardPage />} />

                {/* HR */}
                <Route path="/hr" element={<Navigate to="/hr/employees" replace />} />
                <Route path="/hr/departments" element={ph("modules.hr_departments")} />
                <Route path="/hr/positions"   element={ph("modules.hr_positions")} />
                <Route path="/hr/employees"   element={ph("modules.hr_employees")} />

                {/* Catalog */}
                <Route path="/catalog" element={<Navigate to="/catalog/products" replace />} />
                <Route path="/catalog/categories" element={ph("modules.catalog_categories")} />
                <Route path="/catalog/brands"     element={ph("modules.catalog_brands")} />
                <Route path="/catalog/products"           element={<ProductsListPage />} />
                <Route path="/catalog/products/new"       element={<ProductCreatePage />} />
                <Route path="/catalog/products/:id"       element={<ProductDetailPage />} />
                <Route path="/catalog/products/:id/edit"  element={<ProductEditPage />} />

                {/* Warehouse */}
                <Route path="/warehouse" element={<Navigate to="/warehouse/warehouses" replace />} />
                <Route path="/warehouse/warehouses" element={ph("modules.warehouse_warehouses")} />
                <Route path="/warehouse/stock"      element={ph("modules.warehouse_stock")} />
                <Route path="/warehouse/movements"  element={ph("modules.warehouse_movements")} />
                <Route path="/warehouse/inventory"  element={ph("modules.warehouse_inventory")} />

                {/* Customers */}
                <Route path="/customers" element={ph("modules.customers")} />

                {/* Sales */}
                <Route path="/sales" element={<Navigate to="/sales/orders" replace />} />
                <Route path="/sales/orders"   element={ph("modules.sales_orders")} />
                <Route path="/sales/invoices" element={ph("modules.sales_invoices")} />
                <Route path="/sales/returns"  element={ph("modules.sales_returns")} />

                {/* Procurement */}
                <Route path="/procurement" element={<Navigate to="/procurement/suppliers" replace />} />
                <Route path="/procurement/suppliers" element={ph("modules.procurement_suppliers")} />
                <Route path="/procurement/purchases" element={ph("modules.procurement_purchases")} />

                {/* Finance */}
                <Route path="/finance" element={<Navigate to="/finance/accounts" replace />} />
                <Route path="/finance/accounts" element={ph("modules.finance_accounts")} />
                <Route path="/finance/payments" element={ph("modules.finance_payments")} />
                <Route path="/finance/debts"    element={ph("modules.finance_debts")} />

                {/* Notifications / Audit / Users */}
                <Route path="/notifications" element={ph("modules.notifications")} />
                <Route path="/audit"         element={ph("modules.audit")} />
                <Route path="/users"         element={ph("modules.users")} />
              </Route>
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
          <Toaster richColors position="top-right" />
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

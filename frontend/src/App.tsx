import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { PermissionGate } from "@/components/auth/PermissionGate";
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
import { UserCreatePage } from "@/pages/users/UserCreatePage";
import { UserEditPage } from "@/pages/users/UserEditPage";
import { UsersListPage } from "@/pages/users/UsersListPage";

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

/** Permission talabini routega o'rab beradi — ruxsat bo'lmasa 403 ko'rinishi chiqadi. */
const gate = (perm: string, el: React.ReactNode) => (
  <PermissionGate anyOf={[perm]}>{el}</PermissionGate>
);

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
                <Route
                  path="/hr/departments"
                  element={gate("hr:read", ph("modules.hr_departments"))}
                />
                <Route path="/hr/positions" element={gate("hr:read", ph("modules.hr_positions"))} />
                <Route path="/hr/employees" element={gate("hr:read", ph("modules.hr_employees"))} />

                {/* Catalog */}
                <Route path="/catalog" element={<Navigate to="/catalog/products" replace />} />
                <Route
                  path="/catalog/categories"
                  element={gate("product:read", ph("modules.catalog_categories"))}
                />
                <Route
                  path="/catalog/brands"
                  element={gate("product:read", ph("modules.catalog_brands"))}
                />
                <Route
                  path="/catalog/products"
                  element={gate("product:read", <ProductsListPage />)}
                />
                <Route
                  path="/catalog/products/new"
                  element={gate("product:write", <ProductCreatePage />)}
                />
                <Route
                  path="/catalog/products/:id"
                  element={gate("product:read", <ProductDetailPage />)}
                />
                <Route
                  path="/catalog/products/:id/edit"
                  element={gate("product:write", <ProductEditPage />)}
                />

                {/* Warehouse */}
                <Route
                  path="/warehouse"
                  element={<Navigate to="/warehouse/warehouses" replace />}
                />
                <Route
                  path="/warehouse/warehouses"
                  element={gate("warehouse:read", ph("modules.warehouse_warehouses"))}
                />
                <Route
                  path="/warehouse/stock"
                  element={gate("warehouse:read", ph("modules.warehouse_stock"))}
                />
                <Route
                  path="/warehouse/movements"
                  element={gate("warehouse:read", ph("modules.warehouse_movements"))}
                />
                <Route
                  path="/warehouse/inventory"
                  element={gate("warehouse:read", ph("modules.warehouse_inventory"))}
                />

                {/* Customers */}
                <Route path="/customers" element={gate("customer:read", ph("modules.customers"))} />

                {/* Sales */}
                <Route path="/sales" element={<Navigate to="/sales/orders" replace />} />
                <Route
                  path="/sales/orders"
                  element={gate("order:read", ph("modules.sales_orders"))}
                />
                <Route
                  path="/sales/invoices"
                  element={gate("order:read", ph("modules.sales_invoices"))}
                />
                <Route
                  path="/sales/returns"
                  element={gate("order:read", ph("modules.sales_returns"))}
                />

                {/* Procurement */}
                <Route
                  path="/procurement"
                  element={<Navigate to="/procurement/suppliers" replace />}
                />
                <Route
                  path="/procurement/suppliers"
                  element={gate("purchase:read", ph("modules.procurement_suppliers"))}
                />
                <Route
                  path="/procurement/purchases"
                  element={gate("purchase:read", ph("modules.procurement_purchases"))}
                />

                {/* Finance */}
                <Route path="/finance" element={<Navigate to="/finance/accounts" replace />} />
                <Route
                  path="/finance/accounts"
                  element={gate("accounting:read", ph("modules.finance_accounts"))}
                />
                <Route
                  path="/finance/payments"
                  element={gate("accounting:read", ph("modules.finance_payments"))}
                />
                <Route
                  path="/finance/debts"
                  element={gate("accounting:read", ph("modules.finance_debts"))}
                />

                {/* Notifications / Audit / Users */}
                <Route path="/notifications" element={ph("modules.notifications")} />
                <Route path="/audit" element={gate("audit:read", ph("modules.audit"))} />
                <Route path="/users" element={gate("user:read", <UsersListPage />)} />
                <Route path="/users/new" element={gate("user:write", <UserCreatePage />)} />
                <Route path="/users/:id/edit" element={gate("user:write", <UserEditPage />)} />
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

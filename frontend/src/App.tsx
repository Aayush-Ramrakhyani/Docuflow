/**
 * Root app with client-side routing.
 * Public routes (login/register) accessible without auth.
 * All other routes require authentication + org context.
 */

import { useEffect } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Outlet,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/auth-store";
import { AppShell } from "@/components/layout/AppShell";
import { LoginPage } from "@/pages/auth/LoginPage";
import { RegisterPage } from "@/pages/auth/RegisterPage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { DashboardPage } from "@/pages/dashboard/DashboardPage";
import { DocumentsPage } from "@/pages/documents/DocumentsPage";
import { DocumentReviewPage } from "@/pages/documents/DocumentReviewPage";
import { AnalyticsPage } from "@/pages/analytics/AnalyticsPage";
import { TeamPage } from "@/pages/team/TeamPage";
import { SettingsPage } from "@/pages/settings/SettingsPage";

function AuthInitializer({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, setAuth, logout } = useAuthStore();

  // Try to restore session via refresh cookie on app load
  const { isLoading } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      try {
        // Attempt token refresh first
        const refreshRes = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          credentials: "include",
        });
        if (!refreshRes.ok) {
          logout();
          return null;
        }
        const refreshData = await refreshRes.json();
        const meRes = await authApi.me();
        setAuth(meRes.data, refreshData.access_token);
        return meRes.data;
      } catch {
        logout();
        return null;
      }
    },
    enabled: !isAuthenticated,
    retry: false,
  });

  if (isLoading && !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-muted-foreground text-sm animate-pulse">
          Loading DocuFlow…
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function PublicRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthInitializer>
        <Routes>
          {/* Public auth routes */}
          <Route element={<PublicRoute />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          </Route>

          {/* Protected app routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/documents/:documentId/review" element={<DocumentReviewPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/team" element={<TeamPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Route>

          {/* Root redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthInitializer>
    </BrowserRouter>
  );
}

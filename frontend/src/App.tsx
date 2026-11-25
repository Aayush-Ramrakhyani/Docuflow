/**
 * Root app with client-side routing.
 * Public routes (login/register) accessible without auth.
 * All other routes require authentication + org context.
 */

import { lazy, Suspense } from "react";
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

// Auth pages are small and on the critical path — load eagerly.
import { LoginPage } from "@/pages/auth/LoginPage";
import { RegisterPage } from "@/pages/auth/RegisterPage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";

// App pages are code-split — heavy deps (recharts, react-pdf) load only when
// the route is visited, keeping the initial bundle small.
const DashboardPage = lazy(() =>
  import("@/pages/dashboard/DashboardPage").then((m) => ({ default: m.DashboardPage }))
);
const DocumentsPage = lazy(() =>
  import("@/pages/documents/DocumentsPage").then((m) => ({ default: m.DocumentsPage }))
);
const DocumentReviewPage = lazy(() =>
  import("@/pages/documents/DocumentReviewPage").then((m) => ({ default: m.DocumentReviewPage }))
);
const AnalyticsPage = lazy(() =>
  import("@/pages/analytics/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage }))
);
const TeamPage = lazy(() =>
  import("@/pages/team/TeamPage").then((m) => ({ default: m.TeamPage }))
);
const SettingsPage = lazy(() =>
  import("@/pages/settings/SettingsPage").then((m) => ({ default: m.SettingsPage }))
);

function PageFallback() {
  return (
    <div className="flex h-full min-h-[50vh] items-center justify-center">
      <div className="text-slate-400 text-sm animate-pulse">Loading…</div>
    </div>
  );
}

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

          {/* Protected app routes — lazy chunks share one Suspense fallback */}
          <Route element={<ProtectedRoute />}>
            <Route
              element={
                <AppShell>
                  <Suspense fallback={<PageFallback />}>
                    <Outlet />
                  </Suspense>
                </AppShell>
              }
            >
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

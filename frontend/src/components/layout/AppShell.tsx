/**
 * Main app shell: sidebar + content area.
 * Protected routes render inside this shell.
 */

import { Outlet } from "react-router-dom";
import { useEffect, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sidebar } from "./Sidebar";
import { useAuthStore } from "@/stores/auth-store";
import { organizationsApi } from "@/api/organizations";

export function AppShell({ children }: { children?: ReactNode }) {
  const { currentOrgId, setCurrentOrg } = useAuthStore();

  // Auto-select first org if none selected
  const { data: orgs } = useQuery({
    queryKey: ["organizations", "my"],
    queryFn: () => organizationsApi.listMine().then((r) => r.data),
  });

  useEffect(() => {
    if (!currentOrgId && orgs && orgs.length > 0) {
      setCurrentOrg(orgs[0].id);
    }
  }, [orgs, currentOrgId, setCurrentOrg]);

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {/* Render explicit children (e.g. a Suspense-wrapped Outlet) when
            provided; otherwise fall back to the router Outlet. */}
        <div className="min-h-full">{children ?? <Outlet />}</div>
      </main>
    </div>
  );
}

/**
 * Main app shell: sidebar + content area.
 * Protected routes render inside this shell.
 */

import { Outlet } from "react-router-dom";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sidebar } from "./Sidebar";
import { useAuthStore } from "@/stores/auth-store";
import { organizationsApi } from "@/api/organizations";

export function AppShell() {
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
        <div className="min-h-full">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

/**
 * Dark-slate sidebar with amber active states.
 * Implements the Arctic Precision navigation pattern.
 */

import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  BarChart3,
  Users,
  Settings,
  LogOut,
  ChevronDown,
  Zap,
  Building2,
} from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { authApi } from "@/api/auth";
import { organizationsApi } from "@/api/organizations";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/documents", label: "Documents", icon: FileText },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/team", label: "Team", icon: Users },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const navigate = useNavigate();
  const { user, currentOrgId, logout } = useAuthStore();

  const { data: orgs } = useQuery({
    queryKey: ["organizations", "my"],
    queryFn: () => organizationsApi.listMine().then((r) => r.data),
  });

  const { data: currentOrg } = useQuery({
    queryKey: ["organization", currentOrgId],
    queryFn: () =>
      organizationsApi.get(currentOrgId!).then((r) => r.data),
    enabled: !!currentOrgId,
  });

  const logoutMutation = useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      logout();
      navigate("/login");
    },
  });

  return (
    <aside className="flex h-screen w-60 flex-col bg-sidebar-bg select-none shrink-0">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 px-5 border-b border-sidebar-hover">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-amber-500">
          <Zap className="h-4 w-4 text-white" />
        </div>
        <span className="text-white font-semibold text-base tracking-tight">
          DocuFlow
        </span>
      </div>

      {/* Organization switcher */}
      <div className="px-3 pt-4 pb-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md hover:bg-sidebar-hover transition-colors group">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-700 shrink-0">
                <Building2 className="h-3.5 w-3.5 text-slate-300" />
              </div>
              <div className="flex-1 text-left min-w-0">
                <div className="text-white text-xs font-medium truncate">
                  {currentOrg?.name ?? "Select org"}
                </div>
                <div className="text-slate-500 text-2xs uppercase tracking-wide">
                  {currentOrg?.plan ?? "free"} plan
                </div>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-slate-500 group-hover:text-slate-400" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-56 bg-slate-800 border-slate-700 text-white"
            align="start"
          >
            {orgs?.map((org) => (
              <DropdownMenuItem
                key={org.id}
                className="text-slate-200 hover:bg-slate-700 cursor-pointer"
                onClick={() => useAuthStore.getState().setCurrentOrg(org.id)}
              >
                <Building2 className="mr-2 h-3.5 w-3.5" />
                {org.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto">
        <div className="text-2xs font-semibold text-slate-600 uppercase tracking-widest px-3 py-2">
          Workspace
        </div>
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors duration-150",
                isActive
                  ? "bg-sidebar-active text-white border-l-[3px] border-amber-500 pl-[9px]"
                  : "text-slate-400 hover:bg-sidebar-hover hover:text-slate-200"
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User footer */}
      <div className="border-t border-sidebar-hover p-3">
        <div className="flex items-center gap-2.5 px-2 py-2 rounded-md hover:bg-sidebar-hover transition-colors">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-amber-500 text-white text-xs font-semibold shrink-0">
            {user?.full_name?.[0]?.toUpperCase() ?? "U"}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-white text-xs font-medium truncate">
              {user?.full_name}
            </div>
            <div className="text-slate-500 text-2xs truncate">{user?.email}</div>
          </div>
          <button
            onClick={() => logoutMutation.mutate()}
            className="p-1 rounded hover:bg-slate-700 transition-colors"
            title="Sign out"
          >
            <LogOut className="h-3.5 w-3.5 text-slate-400 hover:text-white" />
          </button>
        </div>
      </div>
    </aside>
  );
}

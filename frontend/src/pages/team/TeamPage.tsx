import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { UserPlus, Trash2, Shield } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { organizationsApi } from "@/api/organizations";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { formatRelativeTime } from "@/lib/utils";
import type { AxiosError } from "axios";

function RoleBadge({ role }: { role: string }) {
  const styles = {
    owner: "bg-amber-50 text-amber-700 border-amber-200",
    admin: "bg-blue-50 text-blue-700 border-blue-200",
    member: "bg-slate-100 text-slate-600 border-slate-200",
  }[role] ?? "bg-slate-100 text-slate-600 border-slate-200";

  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-2xs font-medium capitalize ${styles}`}>
      {role}
    </span>
  );
}

function InviteModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [error, setError] = useState("");

  const inviteMutation = useMutation({
    mutationFn: () => organizationsApi.inviteMember(orgId, email, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["members", orgId] });
      onClose();
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      setError(err.response?.data?.detail ?? "Failed to invite member");
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/50" onClick={onClose} />
      <div className="relative bg-white rounded-xl border border-slate-200 shadow-modal w-full max-w-md p-6">
        <h3 className="text-base font-semibold text-slate-900 mb-1">Invite team member</h3>
        <p className="text-sm text-slate-500 mb-5">
          They must already have a DocuFlow account.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Email address
            </label>
            <Input
              type="email"
              placeholder="colleague@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full h-9 px-3 text-sm border border-slate-200 rounded-md bg-white focus:outline-none focus:border-amber-500"
            >
              <option value="member">Member — can upload and review documents</option>
              <option value="admin">Admin — can manage team and settings</option>
            </select>
          </div>

          {error && (
            <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex gap-2 justify-end pt-2">
            <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
            <Button
              size="sm"
              onClick={() => inviteMutation.mutate()}
              disabled={!email}
              loading={inviteMutation.isPending}
            >
              Send invite
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function TeamPage() {
  const { currentOrgId, user } = useAuthStore();
  const queryClient = useQueryClient();
  const [showInvite, setShowInvite] = useState(false);

  const { data: members, isLoading } = useQuery({
    queryKey: ["members", currentOrgId],
    queryFn: () =>
      organizationsApi.listMembers(currentOrgId!).then((r) => r.data),
    enabled: !!currentOrgId,
  });

  const removeMutation = useMutation({
    mutationFn: (membershipId: string) =>
      organizationsApi.removeMember(currentOrgId!, membershipId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["members", currentOrgId] }),
  });

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="page-header">
        <div>
          <h1 className="page-title">Team</h1>
          <p className="page-subtitle">Manage team members and their roles</p>
        </div>
        <Button size="sm" onClick={() => setShowInvite(true)}>
          <UserPlus className="h-3.5 w-3.5" />
          Invite member
        </Button>
      </div>

      <Card>
        {isLoading ? (
          <div className="p-6 space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-14 bg-slate-100 rounded animate-pulse" />
            ))}
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="px-5 py-3 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                  Member
                </th>
                <th className="px-5 py-3 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                  Role
                </th>
                <th className="px-5 py-3 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                  Joined
                </th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {members?.map((m) => (
                <tr
                  key={m.id}
                  className="border-b border-slate-100 last:border-0 hover:bg-slate-50"
                >
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-100 text-amber-700 text-sm font-semibold">
                        {(m.user_full_name ?? m.user_email ?? "?")[0].toUpperCase()}
                      </div>
                      <div>
                        <div className="text-sm font-medium text-slate-900">
                          {m.user_full_name ?? "—"}
                          {m.user_id === user?.id && (
                            <span className="ml-1.5 text-2xs text-slate-400">(you)</span>
                          )}
                        </div>
                        <div className="text-xs text-slate-400">{m.user_email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <RoleBadge role={m.role} />
                  </td>
                  <td className="px-5 py-4 text-sm text-slate-400">
                    —
                  </td>
                  <td className="px-5 py-4">
                    {m.role !== "owner" && m.user_id !== user?.id && (
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        className="text-slate-400 hover:text-red-500 hover:bg-red-50"
                        onClick={() => {
                          if (confirm(`Remove ${m.user_full_name ?? m.user_email}?`)) {
                            removeMutation.mutate(m.id);
                          }
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {showInvite && (
        <InviteModal orgId={currentOrgId!} onClose={() => setShowInvite(false)} />
      )}
    </div>
  );
}

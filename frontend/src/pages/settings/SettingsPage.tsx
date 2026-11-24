import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Key, Webhook, Building2, User, Shield } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { organizationsApi } from "@/api/organizations";
import { authApi } from "@/api/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { AxiosError } from "axios";

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Required"),
    new_password: z
      .string()
      .min(8, "Min 8 characters")
      .regex(/[A-Z]/, "Need uppercase")
      .regex(/\d/, "Need a number"),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type PasswordForm = z.infer<typeof passwordSchema>;

function ProfileSection() {
  const { user } = useAuthStore();
  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-amber-700 text-xl font-bold">
            {user?.full_name?.[0]?.toUpperCase()}
          </div>
          <div>
            <div className="font-semibold text-slate-900">{user?.full_name}</div>
            <div className="text-sm text-slate-500">{user?.email}</div>
          </div>
        </div>
        <div className="pt-2 text-xs text-slate-400">
          Profile editing coming soon.
        </div>
      </CardContent>
    </Card>
  );
}

function PasswordSection() {
  const [success, setSuccess] = useState(false);
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<PasswordForm>({ resolver: zodResolver(passwordSchema) });

  const mutation = useMutation({
    mutationFn: (data: PasswordForm) =>
      authApi.changePassword(data.current_password, data.new_password),
    onSuccess: () => {
      reset();
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      setError("root", {
        message: err.response?.data?.detail ?? "Failed to change password",
      });
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Change Password</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={handleSubmit((d) => mutation.mutate(d))}
          className="space-y-4 max-w-sm"
        >
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Current password
            </label>
            <Input
              type="password"
              error={errors.current_password?.message}
              {...register("current_password")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              New password
            </label>
            <Input
              type="password"
              error={errors.new_password?.message}
              {...register("new_password")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Confirm new password
            </label>
            <Input
              type="password"
              error={errors.confirm_password?.message}
              {...register("confirm_password")}
            />
          </div>

          {errors.root && (
            <div className="text-sm text-red-500">{errors.root.message}</div>
          )}
          {success && (
            <div className="text-sm text-green-600 font-medium">
              ✓ Password changed successfully
            </div>
          )}

          <Button type="submit" size="sm" loading={mutation.isPending}>
            Update password
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function OrganizationSection() {
  const { currentOrgId } = useAuthStore();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");

  const { data: org } = useQuery({
    queryKey: ["organization", currentOrgId],
    queryFn: () =>
      organizationsApi.get(currentOrgId!).then((r) => r.data),
    enabled: !!currentOrgId,
  });

  const updateMutation = useMutation({
    mutationFn: () => organizationsApi.update(currentOrgId!, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organization", currentOrgId] });
      setEditing(false);
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Organization</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Organization name
          </label>
          {editing ? (
            <div className="flex gap-2">
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={org?.name}
                className="max-w-xs"
              />
              <Button size="sm" onClick={() => updateMutation.mutate()} loading={updateMutation.isPending}>
                Save
              </Button>
              <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
                Cancel
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-900">{org?.name}</span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => { setName(org?.name ?? ""); setEditing(true); }}
              >
                Edit
              </Button>
            </div>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-500 mb-1">Plan</label>
          <span className="text-sm text-slate-900 capitalize">{org?.plan}</span>
          {" · "}
          <span className="text-sm text-slate-500">
            {org?.documents_used} / {org?.documents_limit} documents
          </span>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-500 mb-1">Slug</label>
          <span className="font-mono text-sm text-slate-600">{org?.slug}</span>
        </div>
      </CardContent>
    </Card>
  );
}

type SettingsTab = "profile" | "organization" | "security";

const TABS: { id: SettingsTab; label: string; icon: React.ElementType }[] = [
  { id: "profile", label: "Profile", icon: User },
  { id: "organization", label: "Organization", icon: Building2 },
  { id: "security", label: "Security", icon: Shield },
];

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Manage your account and organization preferences</p>
        </div>
      </div>

      <div className="flex gap-1 mb-6 border-b border-slate-200">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === id
                ? "text-amber-600 border-amber-500"
                : "text-slate-500 border-transparent hover:text-slate-700"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      <div className="space-y-6">
        {activeTab === "profile" && <ProfileSection />}
        {activeTab === "organization" && <OrganizationSection />}
        {activeTab === "security" && <PasswordSection />}
      </div>
    </div>
  );
}

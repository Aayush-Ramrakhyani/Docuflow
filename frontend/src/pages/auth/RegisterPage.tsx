/**
 * Registration page.
 *
 * Creates the user AND their first organization in one step (the registrant
 * becomes its owner, server-side). The Zod schema mirrors the backend password
 * policy so the user gets instant feedback before submitting.
 */

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Zap } from "lucide-react";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/auth-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AxiosError } from "axios";

const schema = z.object({
  full_name: z.string().min(1, "Full name is required").max(255),
  email: z.string().email("Please enter a valid email"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Must contain at least one uppercase letter")
    .regex(/[a-z]/, "Must contain at least one lowercase letter")
    .regex(/\d/, "Must contain at least one number"),
  organization_name: z.string().min(1, "Organization name is required").max(255),
});

type FormData = z.infer<typeof schema>;

export function RegisterPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const setCurrentOrg = useAuthStore((s) => s.setCurrentOrg);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const registerMutation = useMutation({
    mutationFn: (data: FormData) => authApi.register(data),
    onSuccess: async (res) => {
      // Registration returns tokens immediately — log the user straight in
      setAuth(res.data.user, res.data.access_token);
      const { organizationsApi } = await import("@/api/organizations");
      const orgsRes = await organizationsApi.listMine();
      if (orgsRes.data.length > 0) {
        setCurrentOrg(orgsRes.data[0].id);  // Default into the org just created
      }
      navigate("/dashboard");
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      setError("root", {
        message: err.response?.data?.detail ?? "Registration failed. Please try again.",
      });
    },
  });

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-2.5 mb-8">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-amber-500">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <span className="font-semibold text-slate-900 text-lg">DocuFlow</span>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-8">
          <div className="mb-6">
            <h1 className="text-xl font-bold text-slate-900">Create your workspace</h1>
            <p className="mt-1 text-sm text-slate-500">
              Set up DocuFlow for your team in seconds.
            </p>
          </div>

          <form
            onSubmit={handleSubmit((d) => registerMutation.mutate(d))}
            className="space-y-4"
          >
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Full name
              </label>
              <Input
                type="text"
                placeholder="Alex Johnson"
                autoComplete="name"
                error={errors.full_name?.message}
                {...register("full_name")}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Work email
              </label>
              <Input
                type="email"
                placeholder="alex@company.com"
                autoComplete="email"
                error={errors.email?.message}
                {...register("email")}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Password
              </label>
              <Input
                type="password"
                placeholder="Min. 8 characters with uppercase & numbers"
                autoComplete="new-password"
                error={errors.password?.message}
                {...register("password")}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Organization name
              </label>
              <Input
                type="text"
                placeholder="Acme Corp"
                error={errors.organization_name?.message}
                {...register("organization_name")}
              />
              <p className="mt-1.5 text-xs text-slate-400">
                You can change this later
              </p>
            </div>

            {errors.root && (
              <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700">
                {errors.root.message}
              </div>
            )}

            <Button
              type="submit"
              className="w-full mt-2"
              loading={registerMutation.isPending}
            >
              Create workspace
            </Button>
          </form>

          <p className="mt-5 text-center text-sm text-slate-500">
            Already have an account?{" "}
            <Link to="/login" className="text-amber-600 hover:text-amber-700 font-medium">
              Sign in
            </Link>
          </p>
        </div>

        <p className="mt-6 text-center text-xs text-slate-400">
          By creating an account you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}

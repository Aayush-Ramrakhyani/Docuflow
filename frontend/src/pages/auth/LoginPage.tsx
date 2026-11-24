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
  email: z.string().email("Please enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

type FormData = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const setCurrentOrg = useAuthStore((s) => s.setCurrentOrg);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const loginMutation = useMutation({
    mutationFn: (data: FormData) => authApi.login(data),
    onSuccess: async (res) => {
      setAuth(res.data.user, res.data.access_token);
      // Fetch orgs and select the first one
      const { organizationsApi } = await import("@/api/organizations");
      const orgsRes = await organizationsApi.listMine();
      if (orgsRes.data.length > 0) {
        setCurrentOrg(orgsRes.data[0].id);
      }
      navigate("/dashboard");
    },
    onError: (err: AxiosError<{ detail: string }>) => {
      setError("root", {
        message: err.response?.data?.detail ?? "Invalid email or password",
      });
    },
  });

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Left branding panel */}
      <div className="hidden lg:flex lg:w-96 bg-slate-900 flex-col justify-between p-10">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-amber-500">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <span className="text-white font-semibold text-lg">DocuFlow</span>
        </div>

        <div>
          <blockquote className="text-slate-300 text-base leading-relaxed">
            "DocuFlow reduced our invoice processing time from 4 hours to 20 minutes. The extraction accuracy is remarkable."
          </blockquote>
          <div className="mt-4">
            <div className="text-white text-sm font-medium">Sarah Chen</div>
            <div className="text-slate-500 text-xs">Finance Director, Acme Corp</div>
          </div>
        </div>

        <div className="text-slate-600 text-xs">
          © 2026 DocuFlow. Intelligent document processing.
        </div>
      </div>

      {/* Right login form */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          {/* Logo for small screens */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-amber-500">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <span className="font-semibold text-slate-900 text-base">DocuFlow</span>
          </div>

          <div className="mb-8">
            <h1 className="text-2xl font-bold text-slate-900">Welcome back</h1>
            <p className="mt-1 text-sm text-slate-500">
              Sign in to your DocuFlow workspace
            </p>
          </div>

          <form onSubmit={handleSubmit((d) => loginMutation.mutate(d))} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Work email
              </label>
              <Input
                type="email"
                placeholder="you@company.com"
                autoComplete="email"
                error={errors.email?.message}
                {...register("email")}
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-medium text-slate-700">Password</label>
                <Link
                  to="/forgot-password"
                  className="text-xs text-amber-600 hover:text-amber-700"
                >
                  Forgot password?
                </Link>
              </div>
              <Input
                type="password"
                placeholder="Enter your password"
                autoComplete="current-password"
                error={errors.password?.message}
                {...register("password")}
              />
            </div>

            {errors.root && (
              <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700">
                {errors.root.message}
              </div>
            )}

            <Button
              type="submit"
              className="w-full"
              loading={loginMutation.isPending}
            >
              Sign in
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Don't have an account?{" "}
            <Link to="/register" className="text-amber-600 hover:text-amber-700 font-medium">
              Create workspace
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

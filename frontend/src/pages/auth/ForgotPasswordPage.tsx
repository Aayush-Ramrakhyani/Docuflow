/**
 * Forgot-password page.
 *
 * Always shows the same "check your email" confirmation regardless of whether
 * the address is registered — this mirrors the backend's anti-enumeration
 * behavior, so the UI never reveals which emails have accounts.
 */

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Zap, CheckCircle2 } from "lucide-react";
import { authApi } from "@/api/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const schema = z.object({
  email: z.string().email("Please enter a valid email"),
});

type FormData = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const mutation = useMutation({
    mutationFn: (data: FormData) => authApi.forgotPassword(data.email),
    // Backend always returns 200 — success just flips to the confirmation screen
    onSuccess: () => setSubmitted(true),
  });

  if (submitted) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-6">
        <div className="w-full max-w-sm text-center">
          <div className="flex justify-center mb-4">
            <CheckCircle2 className="h-12 w-12 text-green-500" />
          </div>
          <h1 className="text-xl font-bold text-slate-900">Check your email</h1>
          <p className="mt-2 text-sm text-slate-500 max-w-xs mx-auto">
            If an account exists for that email, you'll receive a password reset link shortly.
          </p>
          <Link
            to="/login"
            className="mt-6 inline-block text-sm text-amber-600 hover:text-amber-700 font-medium"
          >
            Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2.5 mb-8">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-amber-500">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <span className="font-semibold text-slate-900">DocuFlow</span>
        </div>

        <div className="mb-6">
          <h1 className="text-xl font-bold text-slate-900">Reset password</h1>
          <p className="mt-1 text-sm text-slate-500">
            Enter your email and we'll send a reset link.
          </p>
        </div>

        <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Email address
            </label>
            <Input
              type="email"
              placeholder="you@company.com"
              error={errors.email?.message}
              {...register("email")}
            />
          </div>

          <Button type="submit" className="w-full" loading={mutation.isPending}>
            Send reset link
          </Button>
        </form>

        <Link
          to="/login"
          className="mt-6 block text-center text-sm text-slate-500 hover:text-slate-700"
        >
          ← Back to sign in
        </Link>
      </div>
    </div>
  );
}

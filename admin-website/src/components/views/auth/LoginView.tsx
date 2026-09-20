"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { api, ApiRequestError } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { SafeUser } from "@/lib/types";

import { AuthShell, PasswordInput } from "./AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

const schema = z.object({
  email: z.string().min(1, "Enter your email").email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
  remember: z.boolean().default(false),
});

type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

const DEV_ADMIN_CREDENTIALS: { email: string; password: string; label: string }[] = [
  { email: "admin@sentinel.mil", password: "sentinel-admin-2024", label: "Administrator" },
  { email: "mhp@sentinel.mil", password: "sentinel-mhp-2024", label: "Mental Health Professional" },
  { email: "supervisor@sentinel.mil", password: "sentinel-super-2024", label: "Supervisor" },
];

const ADMIN_ROLES = ["ADMIN", "SUPER_ADMIN", "MENTAL_HEALTH_PROFESSIONAL", "SUPERVISOR"];

export default function LoginView() {
  const navigate = useApp((s) => s.navigate);
  const setUser = useApp((s) => s.setUser);

  const [submitting, setSubmitting] = React.useState(false);
  const [lockedMsg, setLockedMsg] = React.useState<string | null>(null);

  const form = useForm<FormInput, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "", remember: false },
  });

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    setLockedMsg(null);
    try {
      const { user } = await api.post<{ user: SafeUser }>("/api/auth/login", {
        email: values.email,
        password: values.password,
      });
      if (!ADMIN_ROLES.includes(user.role)) {
        setLockedMsg("This is the CRPF MHS administrator website. Personnel accounts must use the employee app.");
        return;
      }
      setUser(user);
      const firstName = user.name?.split(" ")[0];
      toast.success(firstName ? `Welcome back, ${firstName}.` : "Welcome back.");
      navigate("admin");
    } catch (err) {
      if (err instanceof ApiRequestError) {
        if (err.status === 423 || err.code === "LOCKED") {
          setLockedMsg(
            err.message ||
              "Account temporarily locked after repeated failed attempts. Please try again later."
          );
        } else if (err.status === 401 || err.code === "INVALID_CREDENTIALS") {
          form.setError("password", { message: "Invalid email or password." });
        } else {
          toast.error(err.message || "Unable to sign in. Please try again.");
        }
      } else {
        toast.error("Network error — please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  function fillDev(email: string, password: string) {
    form.setValue("email", email);
    form.setValue("password", password);
    form.clearErrors("password");
    setLockedMsg(null);
    form.setFocus("password");
  }

  return (
    <AuthShell
      eyebrow="Secure access"
      title="Sign in to CRPF MHS"
      description="Your confidential wellbeing companion for armed forces personnel."
      footer={<p>Personnel access is provided through the CRPF MHS employee app.</p>}
    >
      {lockedMsg && (
        <Alert variant="destructive" className="mb-4">
          <LockKeyhole className="h-4 w-4" />
          <AlertTitle>Account temporarily locked</AlertTitle>
          <AlertDescription>{lockedMsg}</AlertDescription>
        </Alert>
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <div className="relative">
                    <Mail
                      className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                      aria-hidden
                    />
                    <Input
                      type="email"
                      autoComplete="email"
                      inputMode="email"
                      placeholder="you@forces.gov"
                      className="pl-9"
                      aria-invalid={!!form.formState.errors.email}
                      {...field}
                    />
                  </div>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <div className="flex items-center justify-between">
                  <FormLabel>Password</FormLabel>
                  <button
                    type="button"
                    onClick={() => navigate("forgot-password")}
                    className="text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded"
                  >
                    Forgot password?
                  </button>
                </div>
                <FormControl>
                  <PasswordInput
                    autoComplete="current-password"
                    placeholder="••••••••"
                    aria-invalid={!!form.formState.errors.password}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="remember"
            render={({ field }) => (
              <FormItem className="flex flex-row items-center gap-2 space-y-0">
                <FormControl>
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                </FormControl>
                <FormLabel className="text-sm font-normal text-muted-foreground cursor-pointer">
                  Keep me signed in on this device
                </FormLabel>
              </FormItem>
            )}
          />

          <Button type="submit" className="h-10 w-full" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </Form>

      <div className="my-5 flex items-center gap-3" aria-hidden>
        <Separator className="flex-1" />
        <span className="text-xs uppercase tracking-wider text-muted-foreground">
          or
        </span>
        <Separator className="flex-1" />
      </div>

      <Alert className="mt-6 border-dashed bg-muted/40">
        <ShieldCheck className="h-4 w-4 text-muted-foreground" />
        <AlertTitle className="text-xs font-semibold text-muted-foreground">
          Administrator access
        </AlertTitle>
        <AlertDescription className="text-xs text-muted-foreground">
          <p className="mb-2">
            Development-only seeded cloud accounts (remove this panel for production deployments).
          </p>
          <ul className="space-y-1">
            {DEV_ADMIN_CREDENTIALS.map((c) => (
              <li key={c.email}>
                <button
                  type="button"
                  onClick={() => fillDev(c.email, c.password)}
                  className="font-mono text-xs text-primary underline-offset-2 hover:underline"
                >
                  {c.email}
                </button>
                <span className="text-muted-foreground"> — {c.label}</span>
              </li>
            ))}
          </ul>
        </AlertDescription>
      </Alert>
    </AuthShell>
  );
}

"use client";

import { useState } from "react";
import { useApp } from "@/lib/store";

import { toast } from "sonner";
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from "@/components/ui/card";

import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Check, X, ShieldCheck, Server, KeyRound, Database, Settings2, Bell } from "lucide-react";
import {
  AdminPage,
} from "./_shared";

import {
  APP_NAME, APP_TAGLINE, CONSENT_VERSION, PERMISSIONS, PERMISSION_LABELS,
  ROLE_LABELS, SENSITIVE_PERMISSIONS,
} from "@/lib/constants";
import type { Permission, Role } from "@/lib/types";

const ROLES: Role[] = ["USER", "SUPERVISOR", "MENTAL_HEALTH_PROFESSIONAL", "ADMIN", "SUPER_ADMIN"];
const ALL_PERMISSIONS: Permission[] = [
  "VIEW_USER_PROFILE", "VIEW_RISK_INDICATOR", "VIEW_ASSESSMENT", "VIEW_JOURNAL",
  "VIEW_AI_CONVERSATION", "MANAGE_ALERTS", "MANAGE_USERS", "VIEW_ANALYTICS",
  "VIEW_AUDIT_LOGS", "MANAGE_SYSTEM",
];

export default function AdminSettingsView() {
  const { user } = useApp();

  // Settings State
  const [mfaEnabled, setMfaEnabled] = useState(true);
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [retentionPeriod, setRetentionPeriod] = useState("90");

  // Best-effort: AI provider is server-only. We surface it only if explicitly
  // exposed via NEXT_PUBLIC_AI_PROVIDER; otherwise show that it's configured.
  const aiProvider = process.env.NEXT_PUBLIC_AI_PROVIDER ?? null;
  const isDev = process.env.NODE_ENV !== "production";


  return (
    <AdminPage>
      <Header />

      {/* Top row: platform + environment */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Platform</CardTitle>
            <CardDescription>General application information</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-y-3 text-sm sm:grid-cols-2">
              <InfoRow icon={ShieldCheck} label="Application" value={APP_NAME} />
              <InfoRow label="Version" value="1.0.0" />
              <InfoRow label="Consent version" value={CONSENT_VERSION} />
              <InfoRow label="Tagline" value={APP_TAGLINE} full />
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Environment</CardTitle>
            <CardDescription>
              Server-side configuration. Secrets are never exposed to the client.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-y-3 text-sm sm:grid-cols-2">
              <InfoRow
                icon={Server}
                label="Node env"
                value={
                  <Badge variant="outline" className={`ring-1 ${isDev ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 ring-amber-200 dark:ring-amber-800" : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 ring-emerald-200 dark:ring-emerald-800"}`}>
                    {process.env.NODE_ENV ?? "—"}
                  </Badge>
                }
              />
              <InfoRow
                icon={KeyRound}
                label="AI provider"
                value={
                  aiProvider ? (
                    <Badge variant="outline" className="ring-1 ring-border">{aiProvider}</Badge>
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      Server-configured (not exposed to client)
                    </span>
                  )
                }
              />
              <InfoRow
                icon={Database}
                label="Database"
                value={<Badge variant="outline" className="ring-1 ring-border">PostgreSQL · shared cloud API</Badge>}
              />
              <InfoRow label="Auth" value={<Badge variant="outline" className="ring-1 ring-border">JWT · HTTP-only BFF cookie</Badge>} />
            </dl>
          </CardContent>
        </Card>
      </div>

      {/* Security & Operations Settings */}
      <Card className="mt-6">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-muted-foreground" />
            Policy preview (demonstration)
          </CardTitle>
          <CardDescription>
            Interface-only policy mockups for the demonstration. These controls do not change cloud enforcement.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-4">
          
          {/* Toggles */}
          <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="mfa" className="text-sm font-medium">Require MFA for Admins</Label>
                <p className="text-xs text-muted-foreground">Force two-factor auth for roles with sensitive access.</p>
              </div>
              <Switch id="mfa" checked={mfaEnabled} onCheckedChange={(val) => { setMfaEnabled(val); toast.success("Demo preference updated for this session"); }} />
            </div>
            
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="alerts" className="text-sm font-medium flex items-center gap-1.5">
                  <Bell className="h-3.5 w-3.5" /> High-Risk Email Alerts
                </Label>
                <p className="text-xs text-muted-foreground">Send immediate emails to supervisors for critical indicators.</p>
              </div>
              <Switch id="alerts" checked={emailAlerts} onCheckedChange={(val) => { setEmailAlerts(val); toast.success("Demo preference updated for this session"); }} />
            </div>
            
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="maintenance" className="text-sm font-medium">Maintenance Mode</Label>
                <p className="text-xs text-muted-foreground">Suspend non-admin access during system updates.</p>
              </div>
              <Switch id="maintenance" checked={maintenanceMode} onCheckedChange={(val) => { setMaintenanceMode(val); toast("Demo preference updated for this session"); }} />
            </div>
          </div>

          {/* Selectors */}
          <div className="flex flex-col gap-6">
            <div className="space-y-2">
              <Label htmlFor="retention" className="text-sm font-medium">Audit Log Retention</Label>
              <Select value={retentionPeriod} onValueChange={(val) => { setRetentionPeriod(val); toast.success("Demo preference updated for this session"); }}>
                <SelectTrigger id="retention" className="w-full sm:w-[240px]">
                  <SelectValue placeholder="Select period" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">30 days (Compliance Min)</SelectItem>
                  <SelectItem value="90">90 days (Standard)</SelectItem>
                  <SelectItem value="365">1 year (Extended)</SelectItem>
                  <SelectItem value="indefinite">Indefinite (Full Archive)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">How long to keep non-sensitive operational audit records.</p>
            </div>
          </div>
          
        </CardContent>
      </Card>

      {/* RBAC permission matrix */}
      <Card className="mt-6">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">RBAC Permission Matrix</CardTitle>
          <CardDescription>
            Role-based access control. Each row is a permission; columns are roles.
            Sensitive permissions (journals, conversations, assessments) are highlighted.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-[240px]">Permission</TableHead>
                  {ROLES.map((r) => (
                    <TableHead key={r} className="text-center">{ROLE_LABELS[r]}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {ALL_PERMISSIONS.map((perm) => {
                  const isSensitive = SENSITIVE_PERMISSIONS.includes(perm);
                  return (
                    <TableRow key={perm} className={isSensitive ? "bg-amber-50/40 dark:bg-amber-500/5" : ""}>
                      <TableCell>
                        <div className="flex items-start gap-2">
                          <div>
                            <p className="text-sm font-medium text-foreground">
                              {PERMISSION_LABELS[perm]}
                            </p>
                            <p className="text-xs text-muted-foreground font-mono">{perm}</p>
                          </div>
                          {isSensitive && (
                            <Badge variant="outline" className="ring-1 ring-amber-200 dark:ring-amber-800 bg-amber-500/10 text-amber-600 dark:text-amber-400">
                              Sensitive
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      {ROLES.map((r) => {
                        const granted = PERMISSIONS[r].includes(perm);
                        return (
                          <TableCell key={r} className="text-center">
                            {granted ? (
                              <Check className="inline-block h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                            ) : (
                              <X className="inline-block h-4 w-4 text-muted-foreground/40" />
                            )}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>


      {/* Signed-in role summary */}
      {user && (
        <Card className="mt-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Your role</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-foreground">
              You are signed in as <span className="font-semibold">{ROLE_LABELS[user.role]}</span>.
              You have{" "}
              <span className="font-semibold">{PERMISSIONS[user.role].length}</span> permission(s):
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {PERMISSIONS[user.role].map((p) => (
                <Badge key={p} variant="outline" className="ring-1 ring-border">
                  {PERMISSION_LABELS[p]}
                </Badge>
              ))}
              {PERMISSIONS[user.role].length === 0 && (
                <span className="text-sm text-muted-foreground">No elevated permissions.</span>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </AdminPage>
  );
}

function InfoRow({
  icon: Icon, label, value, full,
}: {
  icon?: typeof Server; label: string; value: React.ReactNode; full?: boolean;
}) {
  return (
    <div className={`flex items-start justify-between gap-3 ${full ? "sm:col-span-2" : ""}`}>
      <dt className="flex items-center gap-2 text-sm text-muted-foreground">
        {Icon && <Icon className="h-3.5 w-3.5" />}
        {label}
      </dt>
      <dd className="text-right text-sm font-medium text-foreground">{value}</dd>
    </div>
  );
}

function Header() {
  return (
    <div className="mb-6 flex flex-col gap-1">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">System</p>
      <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
        Settings
      </h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Platform information, environment, and the role-based permission matrix.
      </p>
    </div>
  );
}

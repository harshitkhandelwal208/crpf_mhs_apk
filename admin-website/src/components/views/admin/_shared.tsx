"use client";

import { ReactNode } from "react";
import { LockKeyhole, Info } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { PERMISSION_LABELS } from "@/lib/constants";
import type { Permission } from "@/lib/types";

// Common page padding wrapper for admin views (admin-shell's main has no padding).
export function AdminPage({ children }: { children: ReactNode }) {
  return <div className="p-4 sm:p-6 lg:p-8">{children}</div>;
}

// Footnote shown beneath any view that surfaces risk levels.
export function RiskFootnote({ className = "" }: { className?: string }) {
  return (
    <p className={`flex items-start gap-2 text-xs text-muted-foreground ${className}`}>
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>
        These are internal operational wellbeing indicators, not clinical diagnoses.
      </span>
    </p>
  );
}

// Respectful "Access restricted" card shown when the caller lacks a permission.
// Used for sensitive sections (journals, conversations, assessments, etc).
export function RestrictedNotice({ permission }: { permission: Permission }) {
  return (
    <Card className="border-dashed border-[#1d256f]/40 bg-[#1d256f]/5 dark:border-[#1d256f]/60 dark:bg-[#1d256f]/20">
      <CardContent className="flex items-start gap-3 py-5">
        <div className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#1d256f]/15 text-[#1d256f] dark:bg-[#1d256f]/30 dark:text-blue-200">
          <LockKeyhole className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-[#1d256f] dark:text-blue-200">
            Access restricted
          </p>
          <p className="mt-0.5 text-sm text-muted-foreground">
            You don&apos;t have permission to view this section. Required permission:{" "}
            <span className="font-medium text-foreground">
              {PERMISSION_LABELS[permission]}
            </span>
            . Contact a super administrator if access is required.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// Small badge to mark sensitive / audited sections.
export function AuditedBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-800 ring-1 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-400/30">
      <LockKeyhole className="h-3 w-3" />
      Sensitive — access audited
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    OPEN: "bg-rose-500/10 text-rose-600 dark:text-rose-400 ring-1 ring-rose-200 dark:ring-rose-800",
    IN_REVIEW: "bg-sky-500/10 text-sky-600 dark:text-sky-400 ring-1 ring-sky-200 dark:ring-sky-800",
    COMPLETED: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-200 dark:ring-emerald-800",
    REVIEWED: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-200 dark:ring-emerald-800",
    ACKNOWLEDGED: "bg-amber-500/10 text-amber-600 dark:text-amber-400 ring-1 ring-amber-200 dark:ring-amber-800",
    RESOLVED: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-200 dark:ring-emerald-800",
    REJECTED: "bg-red-500/10 text-red-600 dark:text-red-400 ring-1 ring-red-200 dark:ring-red-800",
    FLAGGED: "bg-red-500/10 text-red-600 dark:text-red-400 ring-1 ring-red-200 dark:ring-red-800",
    CRITICAL: "bg-red-500/10 text-red-600 dark:text-red-400 ring-1 ring-red-200 dark:ring-red-800",
    HIGH: "bg-orange-500/10 text-orange-600 dark:text-orange-400 ring-1 ring-orange-200 dark:ring-orange-800",
    ELEVATED: "bg-amber-500/10 text-amber-600 dark:text-amber-400 ring-1 ring-amber-200 dark:ring-amber-800",
    MODERATE: "bg-slate-500/10 text-slate-600 dark:text-slate-400 ring-1 ring-slate-200 dark:ring-slate-800",
    LOW: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-200 dark:ring-emerald-800",
    NORMAL: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-200 dark:ring-emerald-800",
    PENDING: "bg-slate-500/10 text-slate-600 dark:text-slate-400 ring-1 ring-slate-200 dark:ring-slate-800",
    IN_PROGRESS: "bg-blue-500/10 text-blue-600 dark:text-blue-400 ring-1 ring-blue-200 dark:ring-blue-800",
    ASSIGNED: "bg-amber-500/10 text-amber-600 dark:text-amber-400 ring-1 ring-amber-200 dark:ring-amber-800",
    CLOSED: "bg-slate-500/10 text-slate-600 dark:text-slate-400 ring-1 ring-slate-200 dark:ring-slate-800",
  };
  const cls = map[status] ?? "bg-muted text-muted-foreground ring-border";
  const labels: Record<string, string> = {
    OPEN: "Open",
    IN_REVIEW: "In review",
    COMPLETED: "Completed",
    REVIEWED: "Reviewed",
    ACKNOWLEDGED: "Acknowledged",
    RESOLVED: "Resolved",
    REJECTED: "Rejected",
    FLAGGED: "Flagged",
    CRITICAL: "Critical",
    HIGH: "High",
    ELEVATED: "Elevated",
    MODERATE: "Moderate",
    LOW: "Low",
    NORMAL: "Normal",
    PENDING: "Pending",
    IN_PROGRESS: "In progress",
    ASSIGNED: "Assigned",
    CLOSED: "Closed",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${cls}`}>
      {labels[status] ?? status}
    </span>
  );
}

export function SupportStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    OPEN: "bg-rose-500/10 text-rose-600 dark:text-rose-400 ring-1 ring-rose-200 dark:ring-rose-800",
    ASSIGNED: "bg-amber-500/10 text-amber-600 dark:text-amber-400 ring-1 ring-amber-200 dark:ring-amber-800",
    RESOLVED: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-200 dark:ring-emerald-800",
  };
  const cls = map[status] ?? "bg-muted text-muted-foreground ring-border";
  const labels: Record<string, string> = {
    OPEN: "Open", ASSIGNED: "Assigned", RESOLVED: "Resolved",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${cls}`}>
      {labels[status] ?? status}
    </span>
  );
}

// Relative time formatter — short, human.
export function relTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return "just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  if (day < 30) return `${day}d ago`;
  const mo = Math.floor(day / 30);
  if (mo < 12) return `${mo}mo ago`;
  return `${Math.floor(mo / 12)}y ago`;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
  });
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

// Error panel for fetch failures.
export function ErrorPanel({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Card className="border-destructive/30 bg-destructive/5">
      <CardContent className="flex flex-col items-start gap-3 py-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-destructive">Failed to load</p>
          <p className="mt-0.5 text-sm text-muted-foreground">{message}</p>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex h-9 items-center justify-center rounded-md border border-border bg-background px-4 text-sm font-medium hover:bg-accent"
          >
            Retry
          </button>
        )}
      </CardContent>
    </Card>
  );
}

// Permission notice shown when a view is entirely gated by a permission and
// the backend returned 403 (or the local role check fails).
export function PermissionNotice({ permission }: { permission: Permission }) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center gap-3 py-14 text-center">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
          <LockKeyhole className="h-6 w-6" />
        </div>
        <div className="max-w-md">
          <h3 className="text-base font-semibold">Permission required</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            This section requires the{" "}
            <span className="font-medium text-foreground">{PERMISSION_LABELS[permission]}</span>{" "}
            permission. Your current role does not grant access. The backend also enforces this.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// Card skeleton for loading state.
export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <Card className={className}>
      <CardContent className="space-y-3 py-5">
        <div className="h-4 w-24 animate-pulse rounded bg-muted" />
        <div className="h-8 w-32 animate-pulse rounded bg-muted" />
        <div className="h-3 w-20 animate-pulse rounded bg-muted/70" />
      </CardContent>
    </Card>
  );
}

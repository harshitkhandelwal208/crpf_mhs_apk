"use client";

import { type FormEvent, type ReactNode, useEffect, useState, useCallback, useRef } from "react";
import { useApp } from "@/lib/store";
import { api, ApiRequestError } from "@/lib/api";
import {
  Card, CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/shared/ui";
import { LevelDot } from "@/components/shared/level-pill";
import { LEVEL_META } from "@/lib/constants";
import type { PersonnelRowDTO, WellbeingLevel } from "@/lib/types";
import { translate } from "@/lib/i18n";
import {
  AdminPage, ErrorPanel, PermissionNotice, relTime,
} from "./_shared";
import {
  Search, Users, ChevronLeft, ChevronRight, Filter,
  ChevronRight as ChevR, Loader2, Plus, ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";

type Resp = {
  rows: PersonnelRowDTO[]; total: number; page: number; pageSize: number;
  pages: number; units: string[];
};

type PersonnelCreateForm = {
  fullName: string;
  email: string;
  serviceNumber: string;
  rank: string;
  unit: string;
  initialPassword: string;
};

const EMPTY_PERSONNEL_FORM: PersonnelCreateForm = {
  fullName: "",
  email: "",
  serviceNumber: "",
  rank: "",
  unit: "",
  initialPassword: "",
};

const LEVELS: WellbeingLevel[] = ["NORMAL", "LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL"];
const PAGE_SIZE = 12;

const STATUS_STYLE: Record<string, string> = {
  ACTIVE: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800",
  LOCKED: "bg-red-500/10 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800",
  SUSPENDED: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800",
  PENDING_VERIFICATION: "bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800",
};

export default function AdminPersonnelView() {
  const { navigate, params, language, user } = useApp();

  const [q, setQ] = useState(params.q ?? "");
  const [unit, setUnit] = useState(params.unit ?? "all");
  const [level, setLevel] = useState(params.level ?? "all");
  const [page, setPage] = useState(1);

  const [data, setData] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const canManagePersonnel = user?.role === "ADMIN" || user?.role === "SUPER_ADMIN";

  // Debounced search input
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [debouncedQ, setDebouncedQ] = useState(q);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedQ(q);
      setPage(1);
    }, 350);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [q]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setForbidden(false);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("pageSize", String(PAGE_SIZE));
      if (debouncedQ.trim()) params.set("q", debouncedQ.trim());
      if (unit !== "all") params.set("unit", unit);
      if (level !== "all") params.set("level", level);
      const r = await api.get<Resp>(`/api/admin/personnel?${params.toString()}`);
      setData(r);
    } catch (e) {
      if (e instanceof ApiRequestError && e.status === 403) setForbidden(true);
      else setError(e instanceof Error ? e.message : "Failed to load personnel");
    } finally {
      setLoading(false);
    }
  }, [debouncedQ, unit, level, page]);

  useEffect(() => { const id = window.setTimeout(() => { void load(); }, 0); return () => window.clearTimeout(id); }, [load]);

  // Reset to page 1 when filters change
  useEffect(() => { const id = window.setTimeout(() => setPage(1), 0); return () => window.clearTimeout(id); }, [unit, level]);

  if (forbidden) {
    return (
      <AdminPage>
        <Header language={language} />
        <PermissionNotice permission="VIEW_USER_PROFILE" />
      </AdminPage>
    );
  }

  return (
    <AdminPage>
      <Header
        language={language}
        canCreate={canManagePersonnel}
        onCreate={() => setCreateOpen(true)}
      />

      <CreatePersonnelDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={() => {
          setPage(1);
          void load();
        }}
      />

      {/* Filters */}
      <Card className="mb-4 rounded-xl border border-border/60 bg-card shadow-sm">
        <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={translate("Search by name, service number, or email…", language)}
              className="pl-9"
              aria-label={translate("Search personnel", language)}
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
              <FilterSelect
              value={unit} onChange={setUnit}
              placeholder={translate("All units", language)}
              items={(data?.units ?? []).map((u) => ({ value: u, label: u }))}
              ariaLabel={translate("Filter by unit", language)}
            />
            <FilterSelect
              value={level} onChange={setLevel}
              placeholder={translate("All levels", language)}
              items={LEVELS.map((l) => ({ value: l, label: LEVEL_META[l].label }))}
              ariaLabel={translate("Filter by wellbeing level", language)}
            />
            {(q || unit !== "all" || level !== "all") && (
              <Button
                variant="ghost" size="sm"
                onClick={() => { setQ(""); setUnit("all"); setLevel("all"); setPage(1); }}
              >
                {translate("Clear", language)}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Body */}
      {loading ? (
        <PersonnelSkeleton />
      ) : error ? (
        <ErrorPanel message={error} onRetry={load} />
      ) : !data || data.rows.length === 0 ? (
        <Card>
          <CardContent>
            <EmptyState
              icon={Users}
              title="No personnel found"
              description="Try adjusting your search or filters."
            />
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Desktop table */}
          <Card className="hidden rounded-xl border border-border/60 bg-card shadow-sm md:block">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="font-serif text-foreground">{translate("Personnel", language)}</TableHead>
                    <TableHead className="font-serif text-foreground">{translate("Unit", language)}</TableHead>
                    <TableHead className="font-serif text-foreground">{translate("Status", language)}</TableHead>
                    <TableHead className="font-serif text-foreground">{translate("Wellbeing Indicator", language)}</TableHead>
                    <TableHead className="font-serif text-foreground">{translate("Last Check-in", language)}</TableHead>
                    <TableHead className="font-serif text-foreground">{translate("Last Activity", language)}</TableHead>
                    <TableHead className="font-serif text-foreground text-right">{translate("Actions", language)}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.rows.map((p) => (
                    <TableRow key={p.id} className="transition-colors hover:bg-muted/40">
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                            {(p.name?.[0] ?? "?").toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <p className="truncate font-medium text-foreground">{p.name ?? "Unknown"}</p>
                            <p className="truncate text-xs text-muted-foreground">
                              {p.serviceNumber ?? "—"}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm">{p.unit ?? "Unassigned"}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`rounded-sm px-2 py-0.5 font-mono text-[11px] uppercase tracking-[0.08em] ring-1 ${STATUS_STYLE[p.status] ?? ""}`}>
                          {p.status.replace(/_/g, " ").toLowerCase()}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {p.wellbeingLevel ? <LevelDot level={p.wellbeingLevel} /> : <span className="text-muted-foreground text-sm">—</span>}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground tabular-nums">{relTime(p.lastCheckIn)}</TableCell>
                      <TableCell className="text-sm text-muted-foreground tabular-nums">{relTime(p.lastActivity)}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost" size="sm"
                          onClick={() => navigate("admin-person", { id: p.id })}
                        >
                          {translate("View", language)} <ChevR className="ml-1 h-3 w-3" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Mobile cards */}
          <div className="grid grid-cols-1 gap-3 md:hidden">
            {data.rows.map((p) => (
              <Card key={p.id} className="rounded-xl border border-border/60 bg-card shadow-sm">
                <CardContent className="py-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                        {(p.name?.[0] ?? "?").toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate font-medium text-foreground">{p.name ?? "Unknown"}</p>
                        <p className="truncate text-xs text-muted-foreground">
                          {p.serviceNumber ?? "—"}
                        </p>
                      </div>
                    </div>
                    {p.wellbeingLevel && <LevelDot level={p.wellbeingLevel} />}
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-y-1.5 text-xs">
                    <div className="text-muted-foreground">Unit</div>
                    <div className="text-right font-medium">{p.unit ?? "—"}</div>
                    <div className="text-muted-foreground">Status</div>
                    <div className="text-right">
                      <Badge variant="outline" className={`rounded-sm px-2 py-0.5 font-mono text-[11px] uppercase tracking-[0.08em] ring-1 ${STATUS_STYLE[p.status] ?? ""}`}>
                        {p.status.replace(/_/g, " ").toLowerCase()}
                      </Badge>
                    </div>
                    <div className="text-muted-foreground">Last check-in</div>
                    <div className="text-right tabular-nums">{relTime(p.lastCheckIn)}</div>
                    <div className="text-muted-foreground">Last activity</div>
                    <div className="text-right tabular-nums">{relTime(p.lastActivity)}</div>
                  </div>
                  <Button
                    variant="outline" size="sm" className="mt-3 w-full"
                    onClick={() => navigate("admin-person", { id: p.id })}
                  >
                    {translate("View profile", language)}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Pagination */}
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            pageSize={data.pageSize}
            onChange={setPage}
          />
        </>
      )}
    </AdminPage>
  );
}

function CreatePersonnelDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<PersonnelCreateForm>(EMPTY_PERSONNEL_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update(field: keyof PersonnelCreateForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function handleOpenChange(nextOpen: boolean) {
    if (submitting) return;
    onOpenChange(nextOpen);
    if (!nextOpen) {
      setForm(EMPTY_PERSONNEL_FORM);
      setError(null);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.post<PersonnelRowDTO>("/api/admin/personnel", form);
      toast.success("Personnel account created", {
        description: "The account can now sign in through the mobile application.",
      });
      setForm(EMPTY_PERSONNEL_FORM);
      onOpenChange(false);
      onCreated();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not create account");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <div className="mb-1 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <DialogTitle className="font-serif text-xl">Enroll personnel</DialogTitle>
          <DialogDescription>
            Create a mobile account and operational profile. Share the initial password through an approved channel; it is never retained by this console.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={submit} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Full name" htmlFor="personnel-name">
              <Input
                id="personnel-name"
                value={form.fullName}
                onChange={(event) => update("fullName", event.target.value)}
                autoComplete="off"
                maxLength={255}
                required
              />
            </FormField>
            <FormField label="Official email" htmlFor="personnel-email">
              <Input
                id="personnel-email"
                type="email"
                value={form.email}
                onChange={(event) => update("email", event.target.value)}
                autoComplete="off"
                maxLength={255}
                required
              />
            </FormField>
            <FormField label="Service number" htmlFor="personnel-service-number">
              <Input
                id="personnel-service-number"
                value={form.serviceNumber}
                onChange={(event) => update("serviceNumber", event.target.value)}
                autoComplete="off"
                maxLength={50}
                required
              />
            </FormField>
            <FormField label="Rank" htmlFor="personnel-rank">
              <Input
                id="personnel-rank"
                value={form.rank}
                onChange={(event) => update("rank", event.target.value)}
                autoComplete="off"
                maxLength={50}
                required
              />
            </FormField>
            <FormField label="Unit" htmlFor="personnel-unit">
              <Input
                id="personnel-unit"
                value={form.unit}
                onChange={(event) => update("unit", event.target.value)}
                autoComplete="off"
                maxLength={100}
                required
              />
            </FormField>
            <FormField label="Initial password" htmlFor="personnel-password">
              <Input
                id="personnel-password"
                type="password"
                value={form.initialPassword}
                onChange={(event) => update("initialPassword", event.target.value)}
                autoComplete="new-password"
                minLength={12}
                maxLength={128}
                required
              />
            </FormField>
          </div>

          <p className="rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs leading-relaxed text-muted-foreground">
            Passwords require at least 12 characters with uppercase, lowercase, a number, and a symbol. Development demonstration passwords are blocked.
          </p>

          {error && (
            <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}
              Create mobile account
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function FormField({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
    </div>
  );
}

function FilterSelect({
  value, onChange, placeholder, items, ariaLabel,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  items: { value: string; label: string }[];
  ariaLabel: string;
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger aria-label={ariaLabel} className="w-40">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">{placeholder}</SelectItem>
        {items.map((it) => (
          <SelectItem key={it.value} value={it.value}>{it.label}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function Pagination({
  page, pages, total, pageSize, onChange,
}: {
  page: number; pages: number; total: number; pageSize: number;
  onChange: (p: number) => void;
}) {
  const language = useApp((s) => s.language);
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  return (
    <div className="mt-4 flex flex-col items-center justify-between gap-3 sm:flex-row">
      <p className="text-xs text-muted-foreground tabular-nums">
        {translate("Showing", language)} <span className="font-medium text-foreground">{from}</span>–
        <span className="font-medium text-foreground">{to}</span> of{" "}
        <span className="font-medium text-foreground">{total.toLocaleString()}</span>
      </p>
      <div className="flex items-center gap-1">
        <Button
          variant="outline" size="sm"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" /> Prev
        </Button>
        <span className="px-3 text-sm tabular-nums text-muted-foreground">
          {translate("Page", language)} {page} {translate("of", language)} {Math.max(1, pages)}
        </span>
        <Button
          variant="outline" size="sm"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
          aria-label="Next page"
        >
          Next <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function PersonnelSkeleton() {
  return (
    <Card>
      <CardContent className="p-0">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 border-b border-border p-3 last:border-0">
            <Skeleton className="h-9 w-9 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-24" />
            </div>
            <Skeleton className="h-6 w-20" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function Header({
  language,
  canCreate = false,
  onCreate,
}: {
  language: "en" | "hi";
  canCreate?: boolean;
  onCreate?: () => void;
}) {
  return (
    <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div className="flex flex-col gap-1">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">{translate("Directory", language)}</p>
        <h1 className="font-serif text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
          {translate("Personnel", language)}
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          {translate("Search and review operational records. Sensitive clinical content is restricted to authorized roles.", language)}
        </p>
      </div>
      {canCreate && onCreate && (
        <Button onClick={onCreate} className="shrink-0">
          <Plus className="mr-2 h-4 w-4" />
          {translate("Enroll personnel", language)}
        </Button>
      )}
    </div>
  );
}

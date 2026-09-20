"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  AudioLines,
  BedDouble,
  CameraOff,
  Clock3,
  EyeOff,
  Gauge,
  Keyboard,
  ListChecks,
  MapPin,
  RefreshCw,
  ScanEye,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  TriangleAlert,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AdminPage, ErrorPanel } from "./_shared";

interface DemoCamera {
  id: string;
  label: string;
  location: string;
  status: string;
  lastFrameAt: string | null;
  activity: string;
  privacy: string;
}

interface DemoSleep {
  personId: string;
  name: string;
  unit: string;
  restWindow: string;
  estimatedHours: number;
  interruptions: number;
  trend: string;
}

interface DemoVoice {
  personId: string;
  name: string;
  sessionAt: string;
  voiceCracks: number;
  longPauses: number;
  pitchVariance: number;
  confidence: number;
  note: string;
}

interface DemoTyping {
  personId: string;
  name: string;
  sessionAt: string;
  pauseCount: number;
  stuckOn: string | string[];
  correctionRate: number;
  wpm: number;
}

interface DemoHabit {
  label: string;
  value: string | number;
  change: string | number;
  status: string;
}

interface DemoMonitoringResponse {
  demo: boolean;
  generatedAt: string;
  cameras: DemoCamera[];
  sleep: DemoSleep[];
  voice: DemoVoice[];
  typing: DemoTyping[];
  habits: DemoHabit[];
}

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

export default function AdminMonitoringView() {
  const [data, setData] = useState<DemoMonitoringResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestRef = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    setLoading(true);
    setError(null);

    try {
      const response = await api.get<DemoMonitoringResponse>(
        "/api/admin/monitoring/demo",
        { signal: controller.signal },
      );
      if (response.demo !== true) {
        throw new Error("The response was not marked as synthetic demonstration data.");
      }
      setData(response);
    } catch (caught) {
      if (!controller.signal.aborted) {
        setError(caught instanceof Error ? caught.message : "Could not load demonstration monitoring data");
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
      if (requestRef.current === controller) requestRef.current = null;
    }
  }, []);

  useEffect(() => {
    const id = window.setTimeout(() => { void load(); }, 0);
    return () => {
      window.clearTimeout(id);
      requestRef.current?.abort();
    };
  }, [load]);

  return (
    <AdminPage>
      <div className="mx-auto max-w-[1600px] space-y-6" aria-busy={loading}>
        <PageHeader
          generatedAt={data?.generatedAt}
          loading={loading}
          onRefresh={load}
        />
        <DemonstrationBanner />

        {error && (
          <div aria-live="polite">
            <ErrorPanel message={error} onRetry={load} />
          </div>
        )}

        {loading && !data ? (
          <MonitoringSkeleton />
        ) : data ? (
          <MonitoringContent data={data} />
        ) : null}
      </div>
    </AdminPage>
  );
}

function PageHeader({
  generatedAt,
  loading,
  onRefresh,
}: {
  generatedAt?: string;
  loading: boolean;
  onRefresh: () => Promise<void>;
}) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
          Synthetic operational display
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
          Demo Monitoring
        </h1>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">
          A controlled UI demonstration using only values supplied by the demo API.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {generatedAt && (
          <p className="text-xs text-muted-foreground">
            Generated <span className="font-medium text-foreground">{formatDateTime(generatedAt)}</span>
          </p>
        )}
        <Button variant="outline" size="sm" onClick={() => void onRefresh()} disabled={loading}>
          <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          {loading ? "Refreshing" : "Refresh"}
        </Button>
      </div>
    </header>
  );
}

function DemonstrationBanner() {
  return (
    <aside
      className="sticky top-20 z-20 overflow-hidden rounded-xl border-2 border-amber-400 bg-[#0B192C] text-white shadow-lg"
      aria-label="Synthetic demonstration notice"
    >
      <div className="h-1 bg-linear-to-r from-[#FF9933] via-white to-[#138808]" />
      <div className="flex items-start gap-3 px-4 py-4 sm:px-5">
        <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-400 text-[#0B192C]">
          <TriangleAlert className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-extrabold uppercase tracking-[0.08em] text-amber-300 sm:text-base">
            Synthetic demonstration — no live surveillance
          </p>
          <p className="mt-1 text-sm leading-6 text-white/80">
            No CCTV, audio, or keystroke data is collected. Every card below is a mock operational example from the demonstration endpoint.
          </p>
        </div>
      </div>
    </aside>
  );
}

function MonitoringContent({ data }: { data: DemoMonitoringResponse }) {
  const readyCameras = data.cameras.filter((camera) => isPositiveStatus(camera.status)).length;
  const averageRest = data.sleep.length
    ? data.sleep.reduce((total, row) => total + row.estimatedHours, 0) / data.sleep.length
    : 0;
  const interruptions = data.sleep.reduce((total, row) => total + row.interruptions, 0);

  return (
    <div className="space-y-8">
      <section aria-labelledby="demo-overview-heading">
        <SectionHeading
          id="demo-overview-heading"
          icon={Gauge}
          title="Demonstration overview"
          description="Counts and summaries calculated only from the current API response."
        />
        <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <SummaryMetric
            icon={ScanEye}
            label="Mock camera cards"
            value={`${readyCameras}/${data.cameras.length}`}
            detail="API status marked ready"
          />
          <SummaryMetric
            icon={BedDouble}
            label="Estimated rest"
            value={`${formatNumber(averageRest)} h`}
            detail={`${formatNumber(interruptions)} listed interruptions`}
          />
          <SummaryMetric
            icon={AudioLines}
            label="Mock journal sessions"
            value={formatNumber(data.voice.length)}
            detail="No audio collected"
          />
          <SummaryMetric
            icon={Keyboard}
            label="Typing examples"
            value={formatNumber(data.typing.length)}
            detail="Dummy values only"
          />
        </div>
      </section>

      <section aria-labelledby="camera-grid-heading">
        <SectionHeading
          id="camera-grid-heading"
          icon={CameraOff}
          title="CCTV scenario placeholders"
          description="Visual placeholders only. There are no image, stream, recording, or camera source elements in this interface."
        />
        {data.cameras.length ? (
          <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.cameras.map((camera) => (
              <CameraCard key={camera.id} camera={camera} />
            ))}
          </div>
        ) : (
          <EmptyCollection label="No synthetic camera scenarios were supplied." />
        )}
      </section>

      <section aria-labelledby="rest-heading">
        <SectionHeading
          id="rest-heading"
          icon={BedDouble}
          title="Rest schedule demonstration"
          description="Mock schedule estimates for layout review; they are not sleep tracking or health assessment."
        />
        <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <CompactMetric label="Schedules" value={formatNumber(data.sleep.length)} />
          <CompactMetric label="Average estimate" value={`${formatNumber(averageRest)} hours`} />
          <CompactMetric label="Interruptions" value={formatNumber(interruptions)} />
          <CompactMetric
            label="Trend labels"
            value={formatNumber(new Set(data.sleep.map((row) => row.trend)).size)}
          />
        </div>
        <Card className="mt-4 gap-0 overflow-hidden py-0">
          {data.sleep.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Personnel</TableHead>
                  <TableHead>Unit</TableHead>
                  <TableHead>Rest window</TableHead>
                  <TableHead className="text-right">Est. hours</TableHead>
                  <TableHead className="text-right">Interruptions</TableHead>
                  <TableHead>Trend</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.sleep.map((row) => (
                  <TableRow key={`${row.personId}-${row.restWindow}`}>
                    <TableCell className="font-medium">{row.name}</TableCell>
                    <TableCell>{row.unit}</TableCell>
                    <TableCell>{row.restWindow}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatNumber(row.estimatedHours)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatNumber(row.interruptions)}</TableCell>
                    <TableCell><StatusLabel status={row.trend} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyCollection label="No synthetic rest schedules were supplied." />
          )}
        </Card>
      </section>

      <section aria-labelledby="voice-heading">
        <SectionHeading
          id="voice-heading"
          icon={AudioLines}
          title="Mock journal-session signals"
          description="Demonstration indicators for voluntary journal sessions only. No audio is collected here, and these signals are not a diagnosis."
        />
        {data.voice.length ? (
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            {data.voice.map((session) => (
              <VoiceCard key={`${session.personId}-${session.sessionAt}`} session={session} />
            ))}
          </div>
        ) : (
          <EmptyCollection label="No mock journal-session signals were supplied." />
        )}
      </section>

      <section aria-labelledby="typing-heading">
        <SectionHeading
          id="typing-heading"
          icon={Keyboard}
          title="Typing-friction examples"
          description="Dummy pause, correction, and example term values for interface demonstration; no keystrokes are captured."
        />
        {data.typing.length ? (
          <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.typing.map((session) => (
              <TypingCard key={`${session.personId}-${session.sessionAt}`} session={session} />
            ))}
          </div>
        ) : (
          <EmptyCollection label="No dummy typing-friction values were supplied." />
        )}
      </section>

      <section aria-labelledby="habits-heading">
        <SectionHeading
          id="habits-heading"
          icon={ListChecks}
          title="Operational routine metrics"
          description="Synthetic habit and routine summaries supplied by the demonstration API."
        />
        {data.habits.length ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {data.habits.map((habit, index) => (
              <Card key={`${habit.label}-${index}`} className="gap-4 py-5">
                <CardContent>
                  <div className="flex items-start justify-between gap-3">
                    <Activity className="h-5 w-5 text-primary" aria-hidden="true" />
                    <StatusLabel status={habit.status} />
                  </div>
                  <p className="mt-5 text-2xl font-semibold tracking-tight tabular-nums">
                    {formatMetric(habit.value)}
                  </p>
                  <p className="mt-1 text-sm font-medium">{habit.label}</p>
                  <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                    <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
                    Change: {formatMetric(habit.change)}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyCollection label="No synthetic operational routine metrics were supplied." />
        )}
      </section>
    </div>
  );
}

function CameraCard({ camera }: { camera: DemoCamera }) {
  return (
    <Card className="gap-0 overflow-hidden py-0">
      <div
        className="relative flex aspect-video items-center justify-center overflow-hidden bg-[#0B192C] text-white"
        role="img"
        aria-label={`Synthetic visual placeholder for ${camera.label}`}
      >
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,.09) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.09) 1px, transparent 1px)",
            backgroundSize: "28px 28px",
          }}
        />
        <div className="absolute inset-4 rounded-lg border border-dashed border-white/20" />
        <div className="relative flex flex-col items-center gap-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-white/10">
            <ScanEye className="h-6 w-6 text-amber-300" aria-hidden="true" />
          </div>
          <p className="text-xs font-bold uppercase tracking-[0.2em]">Simulated frame</p>
          <p className="text-[11px] text-white/60">No image or video source</p>
        </div>
        <Badge className="absolute left-3 top-3 border-amber-300/40 bg-amber-300/15 text-amber-200">
          DEMO
        </Badge>
      </div>
      <CardContent className="space-y-4 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold">{camera.label}</h3>
            <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
              <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span className="truncate">{camera.location}</span>
            </p>
          </div>
          <StatusLabel status={camera.status} />
        </div>
        <dl className="grid grid-cols-2 gap-3 text-xs">
          <DataPoint label="Mock activity" value={camera.activity} />
          <DataPoint label="Privacy label" value={camera.privacy} />
        </dl>
        <p className="flex items-center gap-1.5 border-t pt-3 text-xs text-muted-foreground">
          <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
          Last synthetic frame: {formatDateTime(camera.lastFrameAt)}
        </p>
      </CardContent>
    </Card>
  );
}

function VoiceCard({ session }: { session: DemoVoice }) {
  return (
    <Card className="gap-4 py-5">
      <CardHeader className="px-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">{session.name}</CardTitle>
            <CardDescription className="mt-1">Mock session · {formatDateTime(session.sessionAt)}</CardDescription>
          </div>
          <Badge variant="outline" className="border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-400/30 dark:bg-violet-400/10 dark:text-violet-300">
            <Sparkles /> Synthetic
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="px-5">
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <DataPoint label="Voice cracks" value={formatNumber(session.voiceCracks)} />
          <DataPoint label="Long pauses" value={formatNumber(session.longPauses)} />
          <DataPoint label="Pitch variance" value={formatNumber(session.pitchVariance)} />
          <DataPoint label="Confidence" value={formatPercent(session.confidence)} />
        </dl>
        <div className="mt-4 rounded-lg border border-dashed bg-muted/35 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Mock note</p>
          <p className="mt-1 text-sm leading-6 text-foreground">{session.note}</p>
        </div>
        <p className="mt-3 flex items-start gap-2 text-xs leading-5 text-muted-foreground">
          <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          Journal-session UI signal only — not a medical or psychological diagnosis.
        </p>
      </CardContent>
    </Card>
  );
}

function TypingCard({ session }: { session: DemoTyping }) {
  const terms = Array.isArray(session.stuckOn) ? session.stuckOn : [session.stuckOn];

  return (
    <Card className="gap-4 py-5">
      <CardHeader className="px-5">
        <CardTitle className="text-base">{session.name}</CardTitle>
        <CardDescription>{formatDateTime(session.sessionAt)} · dummy session</CardDescription>
      </CardHeader>
      <CardContent className="px-5">
        <dl className="grid grid-cols-3 gap-2">
          <DataPoint label="Pauses" value={formatNumber(session.pauseCount)} />
          <DataPoint label="Correction" value={formatPercent(session.correctionRate)} />
          <DataPoint label="WPM" value={formatNumber(session.wpm)} />
        </dl>
        <div className="mt-4 border-t pt-4">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Example “stuck on” terms
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {terms.filter(Boolean).map((term, index) => (
              <Badge key={`${term}-${index}`} variant="secondary" className="whitespace-normal text-left">
                {term}
              </Badge>
            ))}
            {!terms.some(Boolean) && <span className="text-sm text-muted-foreground">None supplied</span>}
          </div>
        </div>
        <p className="mt-4 flex items-start gap-2 text-xs leading-5 text-muted-foreground">
          <EyeOff className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          Dummy display values only; no keystroke capture or background monitoring.
        </p>
      </CardContent>
    </Card>
  );
}

function SectionHeading({
  id,
  icon: Icon,
  title,
  description,
}: {
  id: string;
  icon: typeof Activity;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="h-4 w-4" aria-hidden="true" />
      </div>
      <div>
        <h2 id={id} className="text-lg font-semibold tracking-tight">{title}</h2>
        <p className="mt-0.5 max-w-4xl text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

function SummaryMetric({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: typeof Activity;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <Card className="gap-3 py-4">
      <CardContent className="px-4 sm:px-5">
        <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
        <p className="mt-3 text-2xl font-semibold tracking-tight tabular-nums">{value}</p>
        <p className="mt-1 text-xs font-semibold text-foreground">{label}</p>
        <p className="mt-1 text-[11px] leading-4 text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  );
}

function CompactMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-3 shadow-sm">
      <p className="text-lg font-semibold tabular-nums">{value}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function DataPoint({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg bg-muted/45 p-2.5">
      <dt className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-1 wrap-break-word text-sm font-semibold text-foreground tabular-nums">{value}</dd>
    </div>
  );
}

function StatusLabel({ status }: { status: string }) {
  return (
    <Badge variant="outline" className={cn("max-w-full", statusTone(status))}>
      <span className="truncate">{status}</span>
    </Badge>
  );
}

function EmptyCollection({ label }: { label: string }) {
  return (
    <div className="mt-4 rounded-xl border border-dashed bg-muted/20 px-4 py-10 text-center text-sm text-muted-foreground">
      {label}
    </div>
  );
}

function MonitoringSkeleton() {
  return (
    <div className="space-y-8" role="status" aria-live="polite">
      <span className="sr-only">Loading synthetic demonstration data</span>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Card key={index} className="gap-3 py-4">
            <CardContent className="space-y-3 px-4">
              <Skeleton className="h-5 w-5" />
              <Skeleton className="h-7 w-16" />
              <Skeleton className="h-3 w-28 max-w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
      <div>
        <Skeleton className="h-6 w-52" />
        <Skeleton className="mt-2 h-4 w-96 max-w-full" />
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Card key={index} className="overflow-hidden py-0">
              <Skeleton className="aspect-video w-full rounded-none" />
              <CardContent className="space-y-3 py-4">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-12 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

function isPositiveStatus(status: string): boolean {
  const normalized = status.toLowerCase();
  return ["online", "ready", "active", "available", "stable", "normal", "on track"].some((value) => normalized.includes(value));
}

function statusTone(status: string): string {
  const normalized = status.toLowerCase();
  if (["offline", "blocked", "unavailable", "critical"].some((value) => normalized.includes(value))) {
    return "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-400/30 dark:bg-rose-400/10 dark:text-rose-300";
  }
  if (["attention", "review", "interrupted", "watch", "delayed"].some((value) => normalized.includes(value))) {
    return "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-400/30 dark:bg-amber-400/10 dark:text-amber-300";
  }
  if (isPositiveStatus(status) || ["improving", "complete"].some((value) => normalized.includes(value))) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-400/30 dark:bg-emerald-400/10 dark:text-emerald-300";
  }
  return "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-400/30 dark:bg-slate-400/10 dark:text-slate-300";
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "Not provided";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : DATE_TIME_FORMATTER.format(date);
}

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatPercent(value: number): string {
  const percentage = value >= 0 && value <= 1 ? value * 100 : value;
  return `${percentage.toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
}

function formatMetric(value: string | number): string {
  return typeof value === "number" ? formatNumber(value) : value;
}

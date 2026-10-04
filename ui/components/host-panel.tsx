import { Label } from "@/components/status";
import type { HostMetric, HostView } from "@/lib/derive";
import { ago, clock } from "@/lib/format";
import { cn } from "@/lib/utils";

const NAME: Record<HostMetric["key"], string> = { gpu: "GPU", cpu: "CPU", ram: "RAM", disk: "Disk" };
// More than two sync intervals without a new sample means the sampler or the sync stopped.
const STALE_MS = 15 * 60 * 1000;

export function HostPanel({ host, now }: { host: HostView; now: string }) {
  if (!host) {
    return (
      <section aria-label="VM resources" className="grid gap-2 rounded-lg border bg-card p-4">
        <Label>VM resources</Label>
        <p className="text-sm text-muted-foreground">Waiting for the VM to report. The sampler writes ledger/host.tsv once a minute and it arrives with the next ledger sync.</p>
      </section>
    );
  }
  const stale = Date.parse(now) - Date.parse(host.asOf) > STALE_MS;
  return (
    <section aria-label="VM resources" className="grid gap-3 rounded-lg border bg-card p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <Label>VM resources</Label>
        <span className="text-xs text-muted-foreground">
          <span aria-hidden className={cn("mr-1.5 inline-block size-2 rounded-full align-[1px]", stale ? "bg-bad" : "bg-ok")} />
          Sampled every minute · as of <b className="font-mono text-foreground">{clock(host.asOf)} UTC</b>, {ago(host.asOf, now)}
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {host.metrics.map((m) => (
          <Metric key={m.key} m={m} running={host.running} />
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1.5">
          <i className="inline-block h-2.5 w-3.5 border bg-accent" />
          agent run in progress
        </span>
        <span>last 6 hours · hover a chart for the peak</span>
      </div>
    </section>
  );
}

function Metric({ m, running }: { m: HostMetric; running: boolean[] }) {
  const pct = m.key === "gpu" || m.key === "cpu";
  const unit = pct ? "%" : " GB";
  const values = m.series.filter((v): v is number => v !== null);
  const peak = values.length ? Math.max(...values) : null;
  return (
    <div className="grid min-w-0 content-start gap-1.5 border-dashed py-3 first:pt-0 not-first:border-t sm:py-0 sm:pr-4 sm:not-first:border-t-0 lg:not-first:border-l lg:not-first:pl-4 sm:[&:nth-child(2)]:border-l sm:[&:nth-child(2)]:pl-4">
      <Label>{NAME[m.key]}</Label>
      <div className="font-mono text-[22px] leading-tight font-semibold">
        {m.now === null ? "–" : pct ? `${Math.round(m.now * 10) / 10}%` : Math.round(m.now * 10) / 10}{" "}
        <small className="text-xs font-normal text-muted-foreground">{pct ? (m.key === "cpu" ? "of all cores" : "utilization") : m.total !== null ? `of ${m.total.toLocaleString("en")} GB` : "GB"}</small>
      </div>
      <span className="text-xs text-muted-foreground">
        {m.key === "disk" ? "Agent workspaces" : "Agent"}{" "}
        <b className="font-mono font-medium text-foreground">{m.agent === null ? "–" : m.key === "cpu" ? `${m.agent} cores` : `${m.agent} GB${m.key === "gpu" ? " VRAM" : ""}`}</b>
        {m.extra ? ` · ${m.extra}` : null}
      </span>
      <Spark series={m.series} running={running} label={`${NAME[m.key]}, last 6 hours${peak === null ? "" : `, peak ${Math.round(peak * 10) / 10}${unit}`}`} />
    </div>
  );
}

function Spark({ series, running, label }: { series: (number | null)[]; running: boolean[]; label: string }) {
  const n = series.length;
  const top = Math.max(...series.map((v) => v ?? 0), 0.0001) * 1.15;
  const x = (i: number) => (n > 1 ? (i / (n - 1)) * 100 : 0);
  const y = (v: number) => 42 - (v / top) * 38;
  const bands: { from: number; to: number }[] = [];
  running.forEach((on, i) => {
    if (on && (i === 0 || !running[i - 1])) bands.push({ from: i, to: i });
    if (on) bands[bands.length - 1].to = i;
  });
  let d = "";
  series.forEach((v, i) => {
    if (v === null) return;
    d += `${d && series[i - 1] !== null ? "L" : "M"}${x(i).toFixed(2)},${y(v).toFixed(2)}`;
  });
  return (
    <svg viewBox="0 0 100 44" preserveAspectRatio="none" className="mt-0.5 block h-11 w-full" role="img" aria-label={label}>
      <title>{label}</title>
      {bands.map((b) => (
        <rect key={b.from} x={x(b.from)} y={0} width={Math.max(x(b.to) - x(b.from), 0.5)} height={44} className="fill-accent" />
      ))}
      <path d={d} fill="none" strokeWidth={1.5} vectorEffect="non-scaling-stroke" className="stroke-primary" />
    </svg>
  );
}

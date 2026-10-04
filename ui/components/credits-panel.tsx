import { Label, Pill } from "@/components/status";
import type { Credit } from "@/lib/derive";
import { amount, clock, dayLabel } from "@/lib/format";
import { cn } from "@/lib/utils";

const WHAT: Record<string, string> = {
  huggingface: "model calls through Inference Providers",
  lambda: "GPU host, billed every hour from launch",
  firecrawl: "Developer Index searches",
};

export function CreditsPanel({ credits }: { credits: Credit[] }) {
  return (
    <section aria-label="Credits" className="grid gap-3.5 rounded-lg border bg-card p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <Label>Credits</Label>
        <span className="text-xs text-muted-foreground">A run stops when any provider hits its limit</span>
      </div>
      {credits.length === 0 ? (
        <p className="text-sm text-muted-foreground">No spend rows yet. The agent writes one per provider at the end of each run.</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3">
          {credits.map((c) => (
            <CreditCard key={c.provider} c={c} />
          ))}
        </div>
      )}
    </section>
  );
}

function CreditCard({ c }: { c: Credit }) {
  const limit = c.limit ?? 0;
  const used = c.left !== null && limit ? limit - c.left : c.spent;
  const pct = limit ? Math.min(100, (used / limit) * 100) : 0;
  const max = Math.max(...c.daily.map((d) => d.amount), 0.0001);
  const week = c.daily.reduce((a, d) => a + d.amount, 0);
  return (
    <div className="grid min-w-0 content-start gap-2 border-dashed py-3 first:pt-0 not-first:border-t lg:px-4 lg:py-0 lg:first:pl-0 lg:not-first:border-t-0 lg:not-first:border-l">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <b className="text-[15px]">{c.name}</b>
        <Pill tone={c.fromProvider ? "ok" : "warn"} title={c.source}>
          {c.fromProvider ? "from provider" : "our estimate"}
        </Pill>
      </div>
      <span className="-mt-1.5 text-xs text-muted-foreground">{WHAT[c.provider] ?? c.source}</span>
      <div className="font-mono text-[26px] leading-tight font-semibold">
        {c.left === null ? "?" : amount(c.left, c.unit)}{" "}
        <small className="text-[13px] font-normal text-muted-foreground">left of {limit ? amount(limit, c.unit) : "?"}</small>
      </div>
      <div className="relative h-2 rounded bg-muted" role="img" aria-label={`${Math.round(pct)}% used`}>
        <i className={cn("absolute inset-y-0 left-0 rounded", pct > 75 ? "bg-bad" : pct > 50 ? "bg-warn" : "bg-primary")} style={{ width: `${pct}%` }} />
      </div>
      <svg className="mt-1 block h-10 w-full" viewBox="0 0 100 40" preserveAspectRatio="none" role="img" aria-label="Spend per day, last 7 days">
        {c.daily.map((d, i) => {
          const w = 100 / c.daily.length;
          const h = Math.max((d.amount / max) * 34, 1);
          return (
            <rect key={d.day} x={i * w + 1} y={38 - h} width={w - 2} height={h} className={cn("fill-primary", i === c.daily.length - 1 ? "opacity-100" : "opacity-35")}>
              <title>{`${dayLabel(d.day)}: ${amount(d.amount, c.unit)}`}</title>
            </rect>
          );
        })}
      </svg>
      {c.billingChangedOn && c.daily.some((d) => d.day === c.billingChangedOn) ? (
        <span className="text-xs text-muted-foreground">
          The {dayLabel(c.billingChangedOn)} bar includes a one-time catch-up: cost now counts every hour since launch, as Lambda bills, not only uptime.
        </span>
      ) : null}
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-xs">
        <Fact k="Spend per day" v={`${dayLabel(c.daily[0].day)} → ${dayLabel(c.daily.at(-1)!.day)}`} />
        <Fact k="Today" v={amount(c.daily.at(-1)!.amount, c.unit)} />
        <Fact k="Last 7 days" v={amount(week, c.unit)} />
        {c.runningSince ? <Fact k="Running since" v={`${dayLabel(c.runningSince.slice(0, 10))} ${c.runningSince.slice(11)} UTC`} /> : null}
        {c.hours !== null ? <Fact k="Billed hours" v={`${c.hours.toFixed(1)} h`} /> : null}
        <Fact k="Runs out" v={c.runsOut} />
        <Fact k="As of" v={`${dayLabel(c.asOf.slice(0, 10))} ${clock(c.asOf)} UTC`} />
      </dl>
    </div>
  );
}

function Fact({ k, v }: { k: string; v: string }) {
  return (
    <>
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="text-right font-mono tabular-nums">{v}</dd>
    </>
  );
}

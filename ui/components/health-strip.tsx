import { Label } from "@/components/status";
import type { Health } from "@/lib/derive";
import { ago, clock } from "@/lib/format";
import { cn } from "@/lib/utils";

// No heartbeat file: liveness is read from the newest ledger rows. The dataset
// mirror runs every 30 minutes, so anything older than 2 hours is worth a look.
const STALE_MS = 2 * 60 * 60 * 1000;

export function HealthStrip({ health, now }: { health: Health; now: string }) {
  const stale = !health.lastActivity || Date.parse(now) - Date.parse(health.lastActivity) > STALE_MS;
  const runTone = health.runState === "stalled" || health.runState === "failed" ? "text-bad" : health.runState === "stopped by budget" ? "text-warn" : health.runState === "running" ? "text-primary" : "";
  const lastError = health.errors24h.at(-1);
  return (
    <section aria-label="Agent health" className="grid grid-cols-1 gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-2 lg:grid-cols-4">
      <Cell>
        <span aria-hidden className={cn("mt-1.5 size-2.5 shrink-0 rounded-full", stale ? "bg-bad ring-3 ring-bad-bg" : "bg-ok ring-3 ring-ok-bg")} />
        <div className="grid min-w-0 gap-0.5">
          <Label>Last activity</Label>
          <b className="font-mono text-[15px] font-semibold">{health.lastActivity ? `${clock(health.lastActivity)} UTC` : "none yet"}</b>
          <Muted>{health.lastActivity ? `${ago(health.lastActivity, now)}${stale ? " · check the host" : ""}` : "no ledger rows yet"}</Muted>
        </div>
      </Cell>
      <Cell>
        <div className="grid min-w-0 gap-0.5">
          <Label>Latest run</Label>
          <b className={cn("text-[15px] font-semibold", runTone)}>{health.runState}</b>
          <Muted>{health.currentRun ? <span className="font-mono">{health.currentRun}</span> : "waiting for the first cron tick"}</Muted>
        </div>
      </Cell>
      <Cell>
        <div className="grid min-w-0 gap-0.5">
          <Label>Runs today</Label>
          <b className="font-mono text-[15px] font-semibold">{health.runsToday}</b>
        </div>
      </Cell>
      <Cell>
        <div className="grid min-w-0 gap-0.5">
          <Label>Errors, 24 h</Label>
          <b className={cn("font-mono text-[15px] font-semibold", health.errors24h.length > 0 && "text-warn")}>{health.errors24h.length}</b>
          <Muted>{lastError ? `${clock(lastError.ts)} ${lastError.why}` : "none"}</Muted>
        </div>
      </Cell>
    </section>
  );
}

function Cell({ children }: { children: React.ReactNode }) {
  return <div className="flex min-w-0 items-start gap-2.5 bg-card px-4 py-3">{children}</div>;
}

function Muted({ children }: { children: React.ReactNode }) {
  return <span className="text-xs break-words text-muted-foreground">{children}</span>;
}

import { cn } from "@/lib/utils";
import type { Outcome } from "@/lib/derive";

const TONE = {
  ok: "bg-ok-bg text-ok",
  warn: "bg-warn-bg text-warn",
  bad: "bg-bad-bg text-bad",
  info: "bg-info-bg text-info",
  muted: "bg-muted text-muted-foreground",
} as const;

export type Tone = keyof typeof TONE;

export function Pill({ tone, children, title }: { tone: Tone; children: React.ReactNode; title?: string }) {
  return (
    <span title={title} className={cn("inline-flex h-5 shrink-0 items-center rounded-full px-2 text-[11px] font-semibold tracking-wide whitespace-nowrap", TONE[tone])}>
      {children}
    </span>
  );
}

const OUTCOME: Record<Outcome, [string, Tone]> = {
  kept: ["kept", "ok"],
  skipped: ["skipped", "bad"],
  acted: ["acted", "info"],
  error: ["error", "warn"],
  info: ["step", "muted"],
};

export function OutcomePill({ outcome }: { outcome: Outcome }) {
  const [label, tone] = OUTCOME[outcome];
  return <Pill tone={tone}>{label}</Pill>;
}

export function verdictTone(verdict: string): Tone {
  if (verdict.startsWith("allows")) return "ok";
  if (verdict === "bans") return "bad";
  return "warn";
}

export function Label({ children, className }: { children: React.ReactNode; className?: string }) {
  return <span className={cn("text-[11px] font-semibold tracking-[0.08em] text-muted-foreground uppercase", className)}>{children}</span>;
}

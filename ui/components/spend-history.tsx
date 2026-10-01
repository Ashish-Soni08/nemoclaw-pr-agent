"use client";

import { useState } from "react";
import { Label } from "@/components/status";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { DayTotals } from "@/lib/derive";
import { cn } from "@/lib/utils";

type Grain = "day" | "month" | "year";
type Period = { key: string; huggingface: number; lambda: number; firecrawl: number; prs: number; days: number };

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const money = (v: number) => `$${v.toFixed(2)}`;

function label(key: string, grain: Grain): string {
  if (grain === "year") return key;
  const [y, m, d] = key.split("-").map(Number);
  return grain === "month" ? `${MONTHS[m - 1]} ${y}` : `${d} ${MONTHS[m - 1]}`;
}

function group(days: DayTotals[], grain: Grain): Period[] {
  const keyOf = (d: string) => (grain === "year" ? d.slice(0, 4) : grain === "month" ? d.slice(0, 7) : d);
  const source = grain === "day" ? days.slice(-14) : days;
  const out = new Map<string, Period>();
  for (const d of source) {
    const k = keyOf(d.day);
    const p = out.get(k) ?? { key: k, huggingface: 0, lambda: 0, firecrawl: 0, prs: 0, days: 0 };
    p.huggingface += d.huggingface;
    p.lambda += d.lambda;
    p.firecrawl += d.firecrawl;
    p.prs += d.prs;
    p.days += 1;
    out.set(k, p);
  }
  return [...out.values()];
}

export function SpendHistory({ days }: { days: DayTotals[] }) {
  const [grain, setGrain] = useState<Grain>("day");
  const periods = group(days, grain);
  return (
    <section aria-label="Spend and output over time" className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Label>Spend and output over time</Label>
        <div role="radiogroup" aria-label="Group by" className="inline-flex overflow-hidden rounded-md border">
          {(["day", "month", "year"] as const).map((g) => (
            <button
              key={g}
              type="button"
              role="radio"
              aria-checked={grain === g}
              onClick={() => setGrain(g)}
              className={cn("px-3 py-1 text-[13px] text-muted-foreground capitalize focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary", grain === g && "bg-accent font-semibold text-foreground")}
            >
              {g}
            </button>
          ))}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs">
        <Key className="bg-primary">Hugging Face $</Key>
        <Key className="bg-info">Lambda $</Key>
        <Key className="rounded-full bg-warn">PRs opened</Key>
        <span className="text-muted-foreground">{grain === "day" ? "last 14 days" : grain === "month" ? "by calendar month, current month so far" : "by year, current year so far"}</span>
      </div>
      {periods.length === 0 ? (
        <p className="text-sm text-muted-foreground">No spend recorded yet.</p>
      ) : (
        <>
          <Chart periods={periods} grain={grain} />
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="capitalize">{grain}</TableHead>
                <TableHead className="text-right">Hugging Face</TableHead>
                <TableHead className="text-right">Lambda</TableHead>
                <TableHead className="text-right">Total $</TableHead>
                <TableHead className="text-right">Firecrawl credits</TableHead>
                <TableHead className="text-right">PRs opened</TableHead>
                <TableHead className="text-right">$ per PR</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="font-mono tabular-nums">
              {periods.toReversed().map((p) => {
                const total = p.huggingface + p.lambda;
                return (
                  <TableRow key={p.key}>
                    <TableCell>
                      {label(p.key, grain)}
                      {grain === "month" && p.days < 28 ? <span className="text-muted-foreground"> ({p.days} d)</span> : null}
                    </TableCell>
                    <TableCell className="text-right">{money(p.huggingface)}</TableCell>
                    <TableCell className="text-right">{money(p.lambda)}</TableCell>
                    <TableCell className="text-right">{money(total)}</TableCell>
                    <TableCell className="text-right">{Math.round(p.firecrawl).toLocaleString("en")}</TableCell>
                    <TableCell className="text-right">{p.prs}</TableCell>
                    <TableCell className="text-right">{p.prs ? money(total / p.prs) : "–"}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </>
      )}
    </section>
  );
}

function Key({ className, children }: { className: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <i className={cn("size-2.5 rounded-xs", className)} />
      {children}
    </span>
  );
}

function Chart({ periods, grain }: { periods: Period[]; grain: Grain }) {
  const W = 760, H = 190, L = 44, R = 30, T = 10, B = 26;
  const maxUsd = Math.max(...periods.map((p) => p.huggingface + p.lambda), 1) * 1.1;
  const maxPr = Math.max(...periods.map((p) => p.prs), 1) * 1.15;
  const bw = (W - L - R) / periods.length;
  const y = (v: number) => T + (H - T - B) * (1 - v / maxUsd);
  const yp = (v: number) => T + (H - T - B) * (1 - v / maxPr);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => (maxUsd / 1.1) * f);
  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="block h-[190px] w-full min-w-[520px]" role="img" aria-label={`Spend per ${grain}`}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className="stroke-border" />
            <text x={L - 6} y={y(v) + 3} textAnchor="end" className="fill-muted-foreground font-mono text-[10px]">${v >= 10 ? Math.round(v) : v.toFixed(1)}</text>
          </g>
        ))}
        {periods.map((p, i) => {
          const x = L + i * bw + bw * 0.18;
          const w = bw * 0.64;
          return (
            <g key={p.key}>
              <rect x={x} y={y(p.lambda)} width={w} height={H - B - y(p.lambda)} className="fill-info hover:opacity-80">
                <title>{`${label(p.key, grain)} · Lambda ${money(p.lambda)}`}</title>
              </rect>
              <rect x={x} y={y(p.lambda + p.huggingface)} width={w} height={y(p.lambda) - y(p.lambda + p.huggingface)} className="fill-primary hover:opacity-80">
                <title>{`${label(p.key, grain)} · Hugging Face ${money(p.huggingface)}`}</title>
              </rect>
              <circle cx={x + w / 2} cy={yp(p.prs)} r={3.5} className="fill-warn">
                <title>{`${p.prs} PRs opened`}</title>
              </circle>
              {periods.length <= 14 ? (
                <text x={x + w / 2} y={H - 8} textAnchor="middle" className="fill-muted-foreground font-mono text-[10px]">{label(p.key, grain)}</text>
              ) : null}
            </g>
          );
        })}
        <text x={W - R + 6} y={T + 8} className="fill-muted-foreground font-mono text-[10px]">PRs</text>
      </svg>
    </div>
  );
}

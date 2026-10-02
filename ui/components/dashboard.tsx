"use client";

import { useMemo, useState } from "react";
import { CreditsPanel } from "@/components/credits-panel";
import { EntryDetail } from "@/components/entry-detail";
import { HealthStrip } from "@/components/health-strip";
import { RunsPanel } from "@/components/runs-panel";
import { SpendHistory } from "@/components/spend-history";
import { Label, OutcomePill, Pill, verdictTone } from "@/components/status";
import { ThemeToggle } from "@/components/theme-toggle";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Outcome, Stage, View } from "@/lib/derive";
import { clock, dayLabel } from "@/lib/format";
import { cn } from "@/lib/utils";

const OUTCOMES: { value: Outcome | "all"; label: string }[] = [
  { value: "all", label: "All outcomes" },
  { value: "acted", label: "Acted on GitHub" },
  { value: "kept", label: "Kept going" },
  { value: "skipped", label: "Skipped" },
  { value: "error", label: "Errors" },
  { value: "info", label: "Steps" },
];

export function Dashboard({ view }: { view: View }) {
  // The funnel and timeline show the latest day; the over-time view covers the rest.
  const day = view.days[0] ?? "";
  const [stage, setStage] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<Outcome | "all">("all");
  const stages = view.stagesByDay[day] ?? [];
  const activeStage = stages.find((s) => s.key === stage) ?? null;

  const rows = useMemo(
    () =>
      view.entries
        .filter((e) => e.day === day)
        .filter((e) => !activeStage || activeStage.phases.includes(e.phase))
        .filter((e) => outcome === "all" || e.outcome === outcome)
        .reverse(),
    [view.entries, day, activeStage, outcome],
  );
  const [picked, setPicked] = useState<string | null>(null);
  const selected = rows.find((r) => r.id === picked) ?? rows[0] ?? null;
  const prsToday = view.entries.filter((e) => e.day === day && e.phase === "pr.opened").length;

  return (
    <main className="mx-auto grid max-w-[1240px] gap-[18px] px-4 pt-5 pb-12 sm:px-5">
      <Tabs defaultValue="activity" className="grid gap-[18px]">
        <header className="grid grid-cols-[1fr_auto] items-center gap-3 sm:grid-cols-[1fr_auto_1fr]">
          <span className="hidden sm:block" />
          <div className="grid justify-items-start gap-1.5 sm:justify-items-center sm:text-center">
            <h1 className="text-xl font-bold tracking-tight">NemoClaw PR Agent: Ledger</h1>
            {view.origin.kind === "sample" ? (
              <Pill tone="warn" title="Set LEDGER_DATASET and HF_TOKEN to read the agent's real ledger">Sample data</Pill>
            ) : (
              <span className="text-xs text-muted-foreground">
                {view.origin.dataset} · read {clock(view.fetchedAt)} UTC
              </span>
            )}
          </div>
          <div className="justify-self-end">
            <ThemeToggle />
          </div>
        </header>

        <HealthStrip health={view.health} now={view.now} />
        <CreditsPanel credits={view.credits} />
        <SpendHistory days={view.history} />

        <div className="flex justify-center border-b pb-2.5">
          <TabsList>
            <TabsTrigger value="activity">Activity</TabsTrigger>
            <TabsTrigger value="runs">Runs</TabsTrigger>
            <TabsTrigger value="repos">Repos</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="activity" className="grid gap-[18px]">
          <Funnel stages={stages} active={stage} onPick={(k) => { setStage(stage === k ? null : k); setPicked(null); }} prs={prsToday} />
          <div className="grid gap-[18px] lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
            <section aria-label="Timeline" className="flex min-w-0 flex-col rounded-lg border bg-card">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b px-3.5 py-3">
                <Label>{activeStage ? `${activeStage.label} · ${rows.length} entries` : `Every decision, newest first · ${rows.length}`}</Label>
                <NativeSelect id="outcome" label="Outcome filter" value={outcome} onChange={(v) => { setOutcome(v as Outcome | "all"); setPicked(null); }}>
                  {OUTCOMES.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </NativeSelect>
              </div>
              <div className="relative lg:min-h-80 lg:flex-1">
              <ol className="max-h-[360px] overflow-y-auto lg:absolute lg:inset-0 lg:max-h-none">
                {rows.length === 0 ? (
                  <li className="px-3.5 py-6 text-sm text-muted-foreground">No entries match this filter.</li>
                ) : (
                  rows.map((e) => (
                    <li key={e.id}>
                      <button
                        type="button"
                        onClick={() => setPicked(e.id)}
                        aria-current={selected?.id === e.id}
                        className={cn(
                          "grid w-full grid-cols-[46px_minmax(0,1fr)_auto] items-start gap-2.5 border-b px-3.5 py-2.5 text-left hover:bg-muted focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary",
                          selected?.id === e.id && "bg-accent hover:bg-accent",
                        )}
                      >
                        <span className="pt-0.5 font-mono text-xs text-muted-foreground">{clock(e.ts)}</span>
                        <span className="min-w-0">
                          <span className="font-mono text-[11px] text-muted-foreground">{e.phase}</span>
                          <span className="block font-medium break-words">{e.subject}: {e.decision}</span>
                          {e.why ? <span className="block text-[13px] break-words text-muted-foreground">{e.why}</span> : null}
                        </span>
                        <OutcomePill outcome={e.outcome} />
                      </button>
                    </li>
                  ))
                )}
              </ol>
              </div>
            </section>
            <section aria-label="Entry detail" className="min-w-0 self-start rounded-lg border bg-card">
              {selected ? <EntryDetail entry={selected} all={view.entries} /> : <p className="p-4 text-sm text-muted-foreground">Pick an entry to see why the agent did it.</p>}
            </section>
          </div>
        </TabsContent>

        <TabsContent value="runs">
          <RunsPanel runs={view.runs} rejections={view.rejections} models={view.models} tokensFromSample={view.tokensFromSample} />
        </TabsContent>

        <TabsContent value="repos">
          <section aria-label="Repo policy verdicts" className="rounded-lg border bg-card">
            <div className="border-b px-3.5 py-3">
              <Label>AI-contribution policy per repo · the agent only works where the verdict allows it</Label>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Repo</TableHead>
                  <TableHead>Verdict</TableHead>
                  <TableHead>What the policy says</TableHead>
                  <TableHead>Read from</TableHead>
                  <TableHead>Checked</TableHead>
                  <TableHead className="text-right">PRs</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {view.repos.length === 0 ? (
                  <TableRow><TableCell colSpan={6} className="text-muted-foreground">No policy checks yet.</TableCell></TableRow>
                ) : (
                  view.repos.map((r) => (
                    <TableRow key={r.repo}>
                      <TableCell className="font-mono text-xs">
                        <a className="text-primary hover:underline" href={`https://github.com/${r.repo}`} target="_blank" rel="noreferrer">{r.repo}</a>
                      </TableCell>
                      <TableCell><Pill tone={verdictTone(r.verdict)}>{r.verdict}</Pill></TableCell>
                      <TableCell className="max-w-[44ch] whitespace-normal">{r.text}</TableCell>
                      <TableCell className="font-mono text-xs whitespace-normal">{r.files}</TableCell>
                      <TableCell className="font-mono text-xs">{dayLabel(r.checked.slice(0, 10))}</TableCell>
                      <TableCell className="text-right font-mono">{r.prs}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </section>
        </TabsContent>
      </Tabs>
    </main>
  );
}

function Funnel({ stages, active, onPick, prs }: { stages: Stage[]; active: string | null; onPick: (k: string) => void; prs: number }) {
  const max = Math.max(...stages.map((s) => s.count), 1);
  return (
    <section aria-label="Daily funnel" className="grid gap-3 rounded-lg border bg-card p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <Label>Today&apos;s funnel · click a stage to filter the timeline</Label>
        <span className="text-xs text-muted-foreground">PRs opened <b className="font-mono text-foreground">{prs}</b></span>
      </div>
      <div className="grid grid-cols-2 gap-y-3.5 sm:grid-cols-3 lg:grid-cols-6">
        {stages.map((s, i) => (
          <button
            key={s.key}
            type="button"
            aria-pressed={active === s.key}
            onClick={() => onPick(s.key)}
            className={cn(
              "grid content-start gap-1.5 border-dashed py-1 pr-3 text-left focus-visible:outline-2 focus-visible:outline-primary",
              i > 0 && "lg:border-l lg:pl-3",
            )}
          >
            <Label>{s.label}</Label>
            <span className={cn("font-mono text-[26px] leading-none font-semibold", active === s.key && "text-primary")}>{s.count}</span>
            <span className="h-1.5 overflow-hidden rounded-full bg-muted">
              <i className="block h-full bg-primary" style={{ width: `${Math.max(4, (s.count / max) * 100)}%` }} />
            </span>
            <span className="text-xs text-muted-foreground">{s.note}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function NativeSelect({ id, label, value, onChange, children }: { id: string; label: string; value: string; onChange: (v: string) => void; children: React.ReactNode }) {
  return (
    <select
      id={id}
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-8 rounded-md border bg-card px-2 text-sm text-foreground focus-visible:outline-2 focus-visible:outline-primary"
    >
      {children}
    </select>
  );
}

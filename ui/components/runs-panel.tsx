"use client";

import { useState } from "react";
import { Label, Pill, type Tone } from "@/components/status";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ModelUse, Rejection, RunRow, RunState, StepUse } from "@/lib/derive";
import { clock, dayLabel, shortUrl, urls } from "@/lib/format";
import { cn } from "@/lib/utils";

const STATE_TONE: Record<RunState, Tone> = {
  running: "info",
  finished: "ok",
  "stopped by budget": "warn",
  stalled: "bad",
  failed: "bad",
};

// Friendlier names for the run_config.tsv keys the agent writes.
const CONFIG_LABEL: Record<string, string> = {
  config: "Config",
  "model.triage": "Triage model",
  "model.fix": "Coder model",
  "model.gate": "Self-review gate model",
  "model.summary": "Summary model",
  "firecrawl.per_run_credits": "Firecrawl per run",
  schedule: "Schedule",
};

const when = (ts: string) => `${dayLabel(ts.slice(0, 10))} ${clock(ts)}`;
const compact = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}k` : String(n));
const usd = (v: number) => `$${v.toFixed(2)}`;

export function RunsPanel({ runs, rejections, models, tokensFromSample }: { runs: RunRow[]; rejections: Rejection[]; models: ModelUse[]; tokensFromSample: boolean }) {
  const [picked, setPicked] = useState(runs[0]?.run ?? null);
  const selected = runs.find((r) => r.run === picked) ?? null;
  const gatePasses = runs.reduce((a, r) => a + r.passedGate, 0);
  const modelTotal = models.reduce((a, m) => a + m.costUsd, 0);

  return (
    <div className="grid gap-[18px]">
      <section aria-label="Runs" className="min-w-0 rounded-lg border bg-card">
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b px-3.5 py-3">
          <Label>Runs · click one for its setup and models</Label>
          <span className="text-xs text-muted-foreground">Stalled means no run end and no new rows for 2 hours</span>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Run</TableHead>
              <TableHead>State</TableHead>
              <TableHead className="text-right">Found</TableHead>
              <TableHead className="text-right">Attempted</TableHead>
              <TableHead className="text-right">Passed gate</TableHead>
              <TableHead className="text-right">PR opened</TableHead>
              <TableHead className="text-right">Merged / closed</TableHead>
              <TableHead className="text-right">Rejected</TableHead>
              <TableHead className="text-right">Tokens</TableHead>
              <TableHead className="text-right">HF $</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.length === 0 ? (
              <TableRow><TableCell colSpan={10} className="text-muted-foreground">No runs yet.</TableCell></TableRow>
            ) : (
              runs.map((r) => (
                <TableRow
                  key={r.run}
                  tabIndex={0}
                  aria-current={r.run === picked}
                  onClick={() => setPicked(r.run)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setPicked(r.run); } }}
                  className={cn("cursor-pointer focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-foreground/60", r.run === picked && "bg-accent hover:bg-accent")}
                >
                  <TableCell>
                    <span className="block font-mono text-xs">{r.run}</span>
                    <span className="text-xs text-muted-foreground">{when(r.started)} UTC</span>
                  </TableCell>
                  <TableCell className="max-w-[30ch] whitespace-normal">
                    <Pill tone={STATE_TONE[r.state]}>{r.state}</Pill>
                    <span className="mt-1 block text-xs text-muted-foreground">{r.stateWhy}</span>
                  </TableCell>
                  <Num v={r.found} />
                  <Num v={r.attempted} />
                  <Num v={r.passedGate} />
                  <Num v={r.opened} />
                  <TableCell className="text-right font-mono tabular-nums">{r.merged} / {r.closed}</TableCell>
                  <TableCell className={cn("text-right font-mono tabular-nums", r.rejected > 0 && "text-bad")}>{r.rejected}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums">{r.tokens === null ? "–" : compact(r.tokens)}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums">{r.costUsd === null ? "–" : usd(r.costUsd)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </section>

      {selected ? <RunDetail run={selected} /> : null}

      {/* Both panels take the taller one's height; bodies scroll past ~6 rows and a footer sits at the bottom. */}
      <div className="grid gap-[18px] lg:grid-cols-2">
        <Panel
          label="Gate rejections · fixes the agent refused to send, and why"
          footer={<><span>{rejections.length} rejected · {gatePasses} passed the gate</span><span>across {runs.length} runs</span></>}
        >
          {rejections.length === 0 ? (
            <Empty title="No rejections yet" body="Every fix so far passed the self-review gate." />
          ) : (
            <ol>
              {rejections.map((r) => (
                <li key={`${r.run}-${r.subject}-${r.ts}`} className="grid gap-1 border-b px-3.5 py-3 last:border-b-0">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <b className="text-sm break-words">{r.subject}</b>
                    <span className="font-mono text-xs text-muted-foreground">{when(r.ts)} · {r.run}</span>
                  </div>
                  <p className="max-w-[68ch] border-l-3 border-bad py-0.5 pl-2.5 text-[13px]">{r.reason || "no reason logged"}</p>
                  {r.evidence ? (
                    <span className="font-mono text-xs break-words text-muted-foreground">{urls(r.evidence).length ? shortUrl(urls(r.evidence)[0]) : r.evidence}</span>
                  ) : null}
                </li>
              ))}
            </ol>
          )}
        </Panel>

        <Panel
          label="Hugging Face tokens by model"
          badge={tokensFromSample ? <Pill tone="warn" title="The agent does not write tokens.tsv yet">sample until the agent logs tokens</Pill> : null}
          footer={
            <>
              <span>Total {usd(modelTotal)} · {compact(models.reduce((a, m) => a + m.tokensIn, 0))} in / {compact(models.reduce((a, m) => a + m.tokensOut, 0))} out</span>
              <span>across {runs.length} runs</span>
            </>
          }
        >
          {models.length === 0 ? (
            <Empty title="No token data yet" body="The agent needs to write ledger/tokens.tsv at the end of each run." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead className="text-right">Runs</TableHead>
                  <TableHead className="text-right">In</TableHead>
                  <TableHead className="text-right">Out</TableHead>
                  <TableHead className="text-right">$</TableHead>
                  <TableHead className="text-right">Share</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="font-mono tabular-nums">
                {models.map((m) => (
                  <TableRow key={m.model}>
                    <TableCell className="max-w-[24ch] truncate text-xs" title={m.model}>{m.model}</TableCell>
                    <TableCell className="text-right">{m.runs}</TableCell>
                    <TableCell className="text-right">{compact(m.tokensIn)}</TableCell>
                    <TableCell className="text-right">{compact(m.tokensOut)}</TableCell>
                    <TableCell className="text-right">{usd(m.costUsd)}</TableCell>
                    <TableCell className="text-right">{modelTotal ? Math.round((m.costUsd / modelTotal) * 100) : 0}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Panel>
      </div>
    </div>
  );
}

function RunDetail({ run }: { run: RunRow }) {
  return (
    <section aria-label="Run detail" className="grid min-w-0 gap-[18px] rounded-lg border bg-card p-4">
      <div className="grid justify-items-start gap-2">
        <Pill tone={STATE_TONE[run.state]}>{run.state}</Pill>
        <h2 className="text-lg font-semibold text-balance">
          <span className="font-mono">{run.run}</span> · {when(run.started)} UTC
        </h2>
      </div>

      <div className="grid gap-2">
        <Label>Configuration this run used</Label>
        {run.config.length === 0 ? (
          <p className="text-sm text-muted-foreground">Not recorded for this run. The agent needs to write ledger/run_config.tsv when a run starts.</p>
        ) : (
          <dl className="grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-x-[18px] gap-y-2.5">
            {run.config.map((c) => (
              <div key={c.key} className="grid min-w-0 gap-0.5">
                <dt><Label>{CONFIG_LABEL[c.key] ?? c.key}</Label></dt>
                <dd className="font-mono text-[13px] break-words">{c.value}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      <div className="grid gap-2">
        <Label>Issues worked on</Label>
        {run.issues.length === 0 && run.runWide.length === 0 ? (
          <p className="text-sm text-muted-foreground">No issue reached triage, a claim or a fix in this run. {run.stateWhy}.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Issue</TableHead>
                <TableHead>Outcome</TableHead>
                <TableHead>Steps (model · tokens · $)</TableHead>
                <TableHead className="text-right">HF $</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {run.issues.map((i) => (
                <TableRow key={i.subject} className="align-top">
                  <TableCell className="font-mono text-xs">{i.subject}</TableCell>
                  <TableCell className="max-w-[28ch] whitespace-normal"><Pill tone={i.tone}>{i.outcome}</Pill></TableCell>
                  <TableCell className="whitespace-normal">
                    <Steps steps={i.steps} />
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums">{i.costUsd === null ? "–" : usd(i.costUsd)}</TableCell>
                </TableRow>
              ))}
              {run.runWide.length > 0 ? (
                <TableRow className="align-top">
                  <TableCell className="text-xs text-muted-foreground">Whole run</TableCell>
                  <TableCell className="max-w-[28ch] text-xs whitespace-normal text-muted-foreground">not tied to one issue</TableCell>
                  <TableCell className="whitespace-normal"><Steps steps={run.runWide} /></TableCell>
                  <TableCell className="text-right font-mono tabular-nums">{usd(run.runWide.reduce((a, x) => a + x.costUsd, 0))}</TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        )}
      </div>
    </section>
  );
}

function Steps({ steps }: { steps: StepUse[] }) {
  if (steps.length === 0) return <span className="text-xs text-muted-foreground">no token rows for this issue</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {steps.map((s) => (
        <span key={`${s.step}-${s.model}`} className="inline-flex items-baseline gap-1.5 rounded-md border px-2 py-0.5 text-xs">
          <b className="font-semibold">{s.step}</b>
          <span className="font-mono text-muted-foreground" title={s.model}>{s.model.split("/").at(-1)}</span>
          <span className="font-mono text-muted-foreground">{compact(s.tokens)} · {usd(s.costUsd)}</span>
          {s.result ? <Pill tone={s.result === "pass" ? "ok" : "bad"}>{s.result}</Pill> : null}
        </span>
      ))}
    </div>
  );
}

function Panel({ label, badge, footer, children }: { label: string; badge?: React.ReactNode; footer: React.ReactNode; children: React.ReactNode }) {
  return (
    <section aria-label={label} className="flex min-w-0 flex-col rounded-lg border bg-card">
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b px-3.5 py-3">
        <Label>{label}</Label>
        {badge}
      </div>
      <div className="min-h-40 flex-1 overflow-y-auto lg:max-h-[360px]">{children}</div>
      <div className="flex flex-wrap justify-between gap-2 border-t px-3.5 py-2.5 text-xs text-muted-foreground">{footer}</div>
    </section>
  );
}

function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="grid h-full min-h-40 place-content-center gap-1 p-4 text-center text-[13px] text-muted-foreground">
      <b className="text-sm text-foreground">{title}</b>
      <span>{body}</span>
    </div>
  );
}

function Num({ v }: { v: number }) {
  return <TableCell className="text-right font-mono tabular-nums">{v}</TableCell>;
}

import { Label, Pill, type Tone } from "@/components/status";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ModelUse, Rejection, RunRow, RunState } from "@/lib/derive";
import { clock, dayLabel, shortUrl, urls } from "@/lib/format";

const STATE_TONE: Record<RunState, Tone> = {
  running: "info",
  finished: "ok",
  "stopped by budget": "warn",
  stalled: "bad",
  failed: "bad",
};

const when = (ts: string) => `${dayLabel(ts.slice(0, 10))} ${clock(ts)}`;
const compact = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}k` : String(n));

export function RunsPanel({ runs, rejections, models, tokensMissing }: { runs: RunRow[]; rejections: Rejection[]; models: ModelUse[]; tokensMissing: boolean }) {
  return (
    <div className="grid gap-[18px]">
      <section aria-label="Runs" className="min-w-0 rounded-lg border bg-card">
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b px-3.5 py-3">
          <Label>Every run · what it found and what came out of it</Label>
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
                <TableRow key={r.run}>
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
                  <TableCell className={`text-right font-mono tabular-nums ${r.rejected ? "text-bad" : ""}`}>{r.rejected}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums">{r.tokens === null ? "–" : compact(r.tokens)}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums">{r.costUsd === null ? "–" : `$${r.costUsd.toFixed(2)}`}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </section>

      <div className="grid items-start gap-[18px] lg:grid-cols-2">
        <section aria-label="Gate rejections" className="min-w-0 rounded-lg border bg-card">
          <div className="border-b px-3.5 py-3">
            <Label>Gate rejections · fixes the agent refused to send, and why</Label>
          </div>
          {rejections.length === 0 ? (
            <p className="px-3.5 py-4 text-sm text-muted-foreground">No rejections yet.</p>
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
                    <span className="font-mono text-xs break-words text-muted-foreground">
                      {urls(r.evidence).length ? shortUrl(urls(r.evidence)[0]) : r.evidence}
                    </span>
                  ) : null}
                </li>
              ))}
            </ol>
          )}
        </section>

        <section aria-label="Tokens by model" className="min-w-0 rounded-lg border bg-card">
          <div className="flex flex-wrap items-baseline justify-between gap-2 border-b px-3.5 py-3">
            <Label>Hugging Face tokens by model</Label>
            {tokensMissing ? <Pill tone="warn" title="The agent does not write tokens.tsv yet">sample until the agent logs tokens</Pill> : null}
          </div>
          {models.length === 0 ? (
            <p className="px-3.5 py-4 text-sm text-muted-foreground">No token rows yet. The agent needs to write ledger/tokens.tsv.</p>
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
                {models.map((m) => {
                  const total = models.reduce((a, x) => a + x.costUsd, 0);
                  return (
                    <TableRow key={m.model}>
                      <TableCell className="max-w-[24ch] truncate text-xs" title={m.model}>{m.model}</TableCell>
                      <TableCell className="text-right">{m.runs}</TableCell>
                      <TableCell className="text-right">{compact(m.tokensIn)}</TableCell>
                      <TableCell className="text-right">{compact(m.tokensOut)}</TableCell>
                      <TableCell className="text-right">${m.costUsd.toFixed(2)}</TableCell>
                      <TableCell className="text-right">{total ? Math.round((m.costUsd / total) * 100) : 0}%</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </section>
      </div>
    </div>
  );
}

function Num({ v }: { v: number }) {
  return <TableCell className="text-right font-mono tabular-nums">{v}</TableCell>;
}

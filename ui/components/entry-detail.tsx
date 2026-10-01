import { Label, OutcomePill } from "@/components/status";
import type { Entry } from "@/lib/derive";
import { clock, dayLabel, shortUrl, urls } from "@/lib/format";
import { cn } from "@/lib/utils";

export function EntryDetail({ entry, all }: { entry: Entry; all: Entry[] }) {
  const links = urls(entry.evidence);
  const evidenceText = links.reduce((t, u) => t.replace(u, ""), entry.evidence).trim();
  // Every row about the same issue or repo: the path this subject took through the pipeline.
  const history = all.filter((e) => e.subject === entry.subject);
  const raw = [entry.ts, entry.run, entry.phase, entry.subject, entry.decision, entry.why, entry.evidence, entry.result].join("\t");

  return (
    <div className="grid gap-[18px] p-4">
      <div className="grid justify-items-start gap-2">
        <OutcomePill outcome={entry.outcome} />
        <h2 className="text-lg font-semibold text-balance break-words">
          {entry.subject}: {entry.decision}
        </h2>
      </div>

      <dl className="grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-x-[18px] gap-y-2.5">
        <Field k="Time" v={`${dayLabel(entry.day)} ${clock(entry.ts)} UTC`} mono />
        <Field k="Run" v={entry.run} mono />
        <Field k="Phase" v={entry.phase} mono />
        <Field k="Result" v={entry.result || "-"} mono />
      </dl>

      {entry.why ? (
        <div className="grid gap-2">
          <Label>Why</Label>
          <p className="max-w-[68ch] border-l-3 border-primary py-1 pl-3 text-[15px]">{entry.why}</p>
        </div>
      ) : null}

      {entry.evidence && entry.evidence !== "-" ? (
        <div className="grid gap-2">
          <Label>Evidence</Label>
          <div className="grid gap-1.5 rounded-md bg-muted px-3 py-2.5 text-[13px]">
            {evidenceText ? <span className="font-mono break-words">{evidenceText}</span> : null}
            {links.map((u) => (
              <a key={u} href={u} target="_blank" rel="noreferrer" className="break-all text-primary hover:underline">
                {shortUrl(u)}
              </a>
            ))}
          </div>
        </div>
      ) : null}

      {history.length > 1 ? (
        <div className="grid gap-2">
          <Label>Everything logged for {entry.subject}</Label>
          <ol className="grid">
            {history.map((h) => (
              <li key={h.id} className={cn("grid grid-cols-[minmax(0,170px)_minmax(0,1fr)] gap-2.5 border-b border-dashed py-1.5 text-[13px] last:border-b-0", h.id === entry.id && "font-semibold")}>
                <span className="font-mono text-xs text-muted-foreground">
                  {h.day.slice(5)} {clock(h.ts)} · {h.phase}
                </span>
                <span className="break-words">
                  {h.decision}
                  {h.result ? <span className="text-muted-foreground"> → {h.result}</span> : null}
                </span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      <div className="grid gap-2">
        <Label>Raw ledger row</Label>
        <pre className="overflow-x-auto rounded-md bg-muted px-3 py-2.5 font-mono text-xs leading-relaxed">{raw}</pre>
      </div>
    </div>
  );
}

function Field({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="grid min-w-0 gap-0.5">
      <dt><Label>{k}</Label></dt>
      <dd className={cn("break-words", mono && "font-mono text-[13px]")}>{v}</dd>
    </div>
  );
}

export function clock(ts: string): string {
  return ts.slice(11, 16);
}

export function dayLabel(day: string): string {
  return new Date(`${day}T00:00:00Z`).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
}

export function ago(ts: string, now: string): string {
  const mins = Math.round((Date.parse(now) - Date.parse(ts)) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.round(hours / 24)} days ago`;
}

export function amount(v: number, unit: "usd" | "credits"): string {
  return unit === "usd" ? `$${v.toFixed(2)}` : Math.round(v).toLocaleString("en");
}

const URL_RE = /https?:\/\/\S+/g;

export function urls(text: string): string[] {
  return text.match(URL_RE) ?? [];
}

export function shortUrl(url: string): string {
  const m = url.match(/github\.com\/([^/]+\/[^/]+)\/(issues|pull)\/(\d+)(#issuecomment-\d+)?/);
  if (m) return `${m[1]}${m[2] === "pull" ? " PR " : "#"}${m[3]}${m[4] ? " comment" : ""}`;
  return url.replace(/^https?:\/\//, "");
}

export function formatMetric(v: number | undefined | null): string {
  if (v === undefined || v === null || Number.isNaN(v)) return "—";
  return v.toFixed(4);
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ru-RU", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function isProduction(aliases: string[]): boolean {
  return aliases.includes("production");
}

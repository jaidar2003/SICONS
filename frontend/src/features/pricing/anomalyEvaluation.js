import dayjs from "dayjs";

export function parseConfirmedAnomalyDates(rawValue) {
  const entries = String(rawValue || "")
    .split(/[\n,;]+/g)
    .map((value) => value.trim())
    .filter(Boolean);

  const dates = [];
  const invalidValues = [];
  const seen = new Set();

  for (const entry of entries) {
    const normalized = /^\d{4}-\d{2}$/.test(entry) ? `${entry}-01` : entry;
    const parsed = dayjs(normalized);
    const canonical = parsed.isValid() ? parsed.format("YYYY-MM-DD") : "";
    if (!parsed.isValid() || canonical !== normalized) {
      invalidValues.push(entry);
      continue;
    }
    if (seen.has(canonical)) continue;
    seen.add(canonical);
    dates.push(canonical);
  }

  return { dates, invalidValues };
}

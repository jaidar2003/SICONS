export function formatCurrency(value) {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function formatNumber(value, digits = 2) {
  return new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number(value));
}

export function formatPercentChange(value) {
  const sign = Number(value) > 0 ? "+" : "";
  return `${sign}${formatNumber(value)}%`;
}

export function variationTone(value) {
  if (value === null || Number.isNaN(Number(value))) return "neutral";
  const variation = Number(value);
  const absolute = Math.abs(variation);
  if (variation < 0) return absolute >= 15 ? "success.main" : "success.dark";
  if (absolute < 5) return "text.secondary";
  if (absolute < 15) return "warning.main";
  return "error.main";
}

export function toApiDate(value) {
  if (!value) return "";
  return value.format("YYYY-MM-DD");
}

export function monthLabel(value) {
  return value?.slice(0, 7) || "-";
}


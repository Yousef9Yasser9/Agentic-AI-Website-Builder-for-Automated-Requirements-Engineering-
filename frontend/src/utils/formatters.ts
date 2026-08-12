export function formatDate(value?: string) {
  if (!value) return "Not saved yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function compactPath(value?: string) {
  if (!value) return "Unavailable";
  const normalized = value.replace(/\\/g, "/");
  const parts = normalized.split("/");
  if (parts.length <= 4) return normalized;
  return `.../${parts.slice(-4).join("/")}`;
}

export function countItems(value: unknown[] | undefined) {
  return Array.isArray(value) ? value.length : 0;
}

export function asJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

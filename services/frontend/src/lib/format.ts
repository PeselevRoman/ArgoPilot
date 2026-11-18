// Display helpers. They only write numbers and dates as text: no number is changed.

// "bell-pepper" -> "Bell pepper"
export function cropLabel(cropId: string): string {
  const words = cropId.replace(/-/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// The label of a plan day. "Today" and "Tomorrow" are the first two days of the plan (the plan's
// own idea of today, not this server's clock); the others are "Fri 20 Nov". The date text is
// formatted in UTC so that no timezone can move it to another day.
export function dayLabel(date: string, index: number): { label: string; date: string } {
  const formatted = new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  })
    .format(new Date(`${date}T00:00:00Z`))
    .replace(",", "");
  if (index === 0) return { label: "Today", date: formatted };
  if (index === 1) return { label: "Tomorrow", date: formatted };
  return { label: formatted, date: formatted };
}

// 18975 -> "18,975"; 341.55 -> "341.55"
export function formatNumber(value: number): string {
  return value.toLocaleString("en-GB", { maximumFractionDigits: 20 });
}

export function plural(count: number, one: string, many: string): string {
  return count === 1 ? one : many;
}

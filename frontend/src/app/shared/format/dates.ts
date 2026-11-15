/** Date helpers for API `day` strings (YYYY-MM-DD, the user's local date). */

export function parseDay(day: string): Date {
  const [y, m, d] = day.split('-').map(Number);
  return new Date(y, m - 1, d);
}

export function formatDay(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function addDays(day: string, n: number): string {
  const date = parseDay(day);
  date.setDate(date.getDate() + n);
  return formatDay(date);
}

const LONG = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
});
const SHORT = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' });
const WEEKDAY = new Intl.DateTimeFormat(undefined, { weekday: 'short' });

/** "Today", "Yesterday" or "Mon, 3 Mar". */
export function dayLabel(day: string, today: string): string {
  if (day === today) return 'Today';
  if (day === addDays(today, -1)) return 'Yesterday';
  return LONG.format(parseDay(day));
}

export function shortDay(day: string): string {
  return SHORT.format(parseDay(day));
}

export function weekday(day: string): string {
  return WEEKDAY.format(parseDay(day));
}

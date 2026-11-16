/** Remembers, per browser, the newest progress card the user has opened. */
const KEY = 'bab.progress.seen';

export function seenCard(): number {
  try {
    return Number(localStorage.getItem(KEY) ?? 0) || 0;
  } catch {
    return 0;
  }
}

export function markCardSeen(n: number): void {
  try {
    if (n > seenCard()) localStorage.setItem(KEY, String(n));
  } catch {
    // Storage blocked: the banner just shows again.
  }
}

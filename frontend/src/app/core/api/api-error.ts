import { HttpErrorResponse } from '@angular/common/http';

/** A short, user-facing message for any failed API call. */
export function apiErrorMessage(
  err: unknown,
  fallback = 'Something went wrong. Try again.',
): string {
  if (!(err instanceof HttpErrorResponse)) return fallback;
  if (err.status === 0) return 'Cannot reach the server. Check your connection.';
  const detail = (err.error as { detail?: unknown } | null)?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0] as { msg?: string };
    if (first.msg) return first.msg.replace(/^Value error, /, '');
  }
  return fallback;
}

export function apiErrorCode(err: unknown): string | null {
  if (!(err instanceof HttpErrorResponse)) return null;
  const code = (err.error as { code?: unknown } | null)?.code;
  return typeof code === 'string' ? code : null;
}

import { HttpErrorResponse } from '@angular/common/http';

import { isWaking } from './wake-retry.interceptor';

/** A short, user-facing message for any failed API call. */
export function apiErrorMessage(
  err: unknown,
  fallback = 'Something went wrong. Try again.',
): string {
  if (!(err instanceof HttpErrorResponse)) return fallback;
  if (err.status === 0) return 'Cannot reach the server. Check your connection.';
  if (isWaking(err)) {
    return 'The server is waking up (it naps when nobody has used it for a while). Try again in a minute.';
  }
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

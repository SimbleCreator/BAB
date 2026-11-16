import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { retry, throwError, timer } from 'rxjs';

/**
 * The free API host puts the server to sleep when nobody has used it for a while, and
 * while it wakes up (or redeploys) requests fail at the gateway: 502, 503, 504 or one of
 * Cloudflare's 52x pages, with no B.A.B error body. Safe requests are tried again a few
 * times with growing pauses, so the user just sees a slower answer instead of an error.
 */
export const WAKE_DELAYS_MS = [3000, 6000, 12000, 20000];

const GATEWAY = new Set([502, 503, 504, 520, 521, 522, 523, 524]);
/** Requests that do no harm when sent twice. Other POSTs (logging food, writing a Bounce
 * plan) are never repeated: the first try may have reached the server. */
const SAFE_POSTS = ['/auth/login', '/auth/refresh', '/auth/google'];

export function isWaking(err: unknown): boolean {
  if (!(err instanceof HttpErrorResponse) || !GATEWAY.has(err.status)) return false;
  const code = (err.error as { code?: unknown } | null)?.code;
  // B.A.B's own 502/503 answers (Bounce busy, Google off) carry a code; only the proxy's
  // "api_unreachable" and bodiless gateway pages mean the server is not up yet.
  return code === undefined || code === null || code === 'api_unreachable';
}

function retryable(req: HttpRequest<unknown>): boolean {
  if (req.method === 'GET' || req.method === 'HEAD') return true;
  return req.method === 'POST' && SAFE_POSTS.some((p) => req.url.endsWith(p));
}

export const wakeRetryInterceptor: HttpInterceptorFn = (req, next) => {
  if (!retryable(req)) return next(req);
  return next(req).pipe(
    retry({
      count: WAKE_DELAYS_MS.length,
      delay: (err: unknown, attempt: number) =>
        isWaking(err) ? timer(WAKE_DELAYS_MS[attempt - 1]) : throwError(() => err),
    }),
  );
};

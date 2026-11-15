import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

const SESSION_ENDPOINTS = /\/auth\/(login|register|refresh|logout)$/;
/** Required by the API on cookie-based endpoints (see backend app/core/cookies.py). */
export const CLIENT_HEADER = 'X-BAB-Client';

function withToken(req: HttpRequest<unknown>, token: string | null): HttpRequest<unknown> {
  return token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;
}

/**
 * Adds the access token to API calls and sends cookies. On a 401 it refreshes the
 * access token once and retries; if that fails the session is over.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  if (!req.url.startsWith(environment.apiBaseUrl)) return next(req);

  const auth = inject(AuthService);
  const apiReq = req.clone({ withCredentials: true, setHeaders: { [CLIENT_HEADER]: 'web' } });
  if (SESSION_ENDPOINTS.test(req.url)) return next(apiReq);

  return next(withToken(apiReq, auth.token())).pipe(
    catchError((err: unknown) => {
      if (!(err instanceof HttpErrorResponse) || err.status !== 401) {
        return throwError(() => err);
      }
      return auth.refresh().pipe(
        catchError(() => {
          auth.sessionLost();
          return throwError(() => err);
        }),
        switchMap((token) => next(withToken(apiReq, token))),
      );
    }),
  );
};

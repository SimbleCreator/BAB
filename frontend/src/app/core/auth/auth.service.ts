import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, finalize, firstValueFrom, map, of, shareReplay, tap } from 'rxjs';

import { AuthApi } from '../api/auth.api';
import { ChangePasswordIn, LoginIn, RegisterIn, TokenOut, UserOut } from '../api/models';

/**
 * Session state. The access token lives only in memory; the refresh token is an
 * httpOnly cookie the browser sends to /auth endpoints.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(AuthApi);
  private readonly router = inject(Router);

  private readonly _token = signal<string | null>(null);
  private readonly _user = signal<UserOut | null>(null);
  private refreshInFlight: Observable<string> | null = null;

  readonly user = this._user.asReadonly();
  readonly isLoggedIn = computed(() => this._user() !== null);
  readonly hasProfile = computed(() => this._user()?.has_profile ?? false);

  token(): string | null {
    return this._token();
  }

  /** Called once at startup: restore the session from the refresh cookie if there is one. */
  restoreSession(): Promise<void> {
    return firstValueFrom(
      this.refresh().pipe(
        map(() => undefined),
        catchError(() => of(undefined)),
      ),
    );
  }

  login(body: LoginIn): Observable<UserOut> {
    return this.api.login(body).pipe(map((t) => this.accept(t)));
  }

  register(body: RegisterIn): Observable<UserOut> {
    return this.api.register(body).pipe(map((t) => this.accept(t)));
  }

  changePassword(body: ChangePasswordIn): Observable<UserOut> {
    return this.api.changePassword(body).pipe(map((t) => this.accept(t)));
  }

  /** Get a new access token. Concurrent callers share one request. */
  refresh(): Observable<string> {
    this.refreshInFlight ??= this.api.refresh().pipe(
      map((t) => {
        this.accept(t);
        return t.access_token;
      }),
      finalize(() => (this.refreshInFlight = null)),
      shareReplay({ bufferSize: 1, refCount: false }),
    );
    return this.refreshInFlight;
  }

  logout(): Observable<void> {
    return this.api.logout().pipe(
      catchError(() => of(undefined)),
      tap(() => this.sessionLost()),
    );
  }

  markProfileComplete(): void {
    this._user.update((u) => (u ? { ...u, has_profile: true } : u));
  }

  /** Clear local state and go to the login page. */
  sessionLost(): void {
    this._token.set(null);
    this._user.set(null);
    void this.router.navigateByUrl('/login');
  }

  private accept(t: TokenOut): UserOut {
    this._token.set(t.access_token);
    this._user.set(t.user);
    return t.user;
  }
}

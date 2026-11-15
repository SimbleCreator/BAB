import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ChangePasswordIn, LoginIn, RegisterIn, TokenOut, UserOut } from './models';

/** Client for the backend `auth` router. */
@Injectable({ providedIn: 'root' })
export class AuthApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/auth`;

  register(body: RegisterIn): Observable<TokenOut> {
    return this.http.post<TokenOut>(`${this.base}/register`, body);
  }

  login(body: LoginIn): Observable<TokenOut> {
    return this.http.post<TokenOut>(`${this.base}/login`, body);
  }

  refresh(): Observable<TokenOut> {
    return this.http.post<TokenOut>(`${this.base}/refresh`, null);
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${this.base}/logout`, null);
  }

  me(): Observable<UserOut> {
    return this.http.get<UserOut>(`${this.base}/me`);
  }

  changePassword(body: ChangePasswordIn): Observable<TokenOut> {
    return this.http.post<TokenOut>(`${this.base}/change-password`, body);
  }
}

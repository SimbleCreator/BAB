import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ProfileIn, ProfileOptionsOut, ProfileOut } from './models';

/** Client for the backend `profile` router. */
@Injectable({ providedIn: 'root' })
export class ProfileApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/profile`;

  get(): Observable<ProfileOut> {
    return this.http.get<ProfileOut>(this.base);
  }

  /** Choices for the "Know me" questions (states, kinds of work, food sources). */
  options(): Observable<ProfileOptionsOut> {
    return this.http.get<ProfileOptionsOut>(`${this.base}/options`);
  }

  save(body: ProfileIn): Observable<ProfileOut> {
    return this.http.put<ProfileOut>(this.base, body);
  }
}

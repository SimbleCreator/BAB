import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ProfileIn, ProfileOut } from './models';

/** Client for the backend `profile` router. */
@Injectable({ providedIn: 'root' })
export class ProfileApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/profile`;

  get(): Observable<ProfileOut> {
    return this.http.get<ProfileOut>(this.base);
  }

  save(body: ProfileIn): Observable<ProfileOut> {
    return this.http.put<ProfileOut>(this.base, body);
  }
}

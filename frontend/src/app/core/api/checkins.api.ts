import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { CheckinIn, CheckinOut, CheckinStatusOut } from './models';

/** Client for the backend `checkins` router. */
@Injectable({ providedIn: 'root' })
export class CheckinsApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/checkins`;

  list(): Observable<CheckinOut[]> {
    return this.http.get<CheckinOut[]>(this.base);
  }

  status(): Observable<CheckinStatusOut> {
    return this.http.get<CheckinStatusOut>(`${this.base}/status`);
  }

  save(day: string, body: CheckinIn): Observable<CheckinOut> {
    return this.http.put<CheckinOut>(`${this.base}/${day}`, body);
  }

  delete(day: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${day}`);
  }
}

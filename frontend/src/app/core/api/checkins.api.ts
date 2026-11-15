import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AdjustmentOut, CheckinIn, CheckinOut, CheckinSavedOut, CheckinStatusOut } from './models';

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

  /** Saving the newest check-in may run the weekly adjustment. */
  save(day: string, body: CheckinIn): Observable<CheckinSavedOut> {
    return this.http.put<CheckinSavedOut>(`${this.base}/${day}`, body);
  }

  adjustments(): Observable<AdjustmentOut[]> {
    return this.http.get<AdjustmentOut[]>(`${this.base}/adjustments`);
  }

  delete(day: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${day}`);
  }
}

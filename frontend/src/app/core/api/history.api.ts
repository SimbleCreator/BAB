import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { HistoryDayOut, MonthOut } from './models';

/** Client for the backend `history` router. */
@Injectable({ providedIn: 'root' })
export class HistoryApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/history`;

  month(month?: string): Observable<MonthOut> {
    const params: Record<string, string> = month ? { month } : {};
    return this.http.get<MonthOut>(`${this.base}/month`, { params });
  }

  day(day: string): Observable<HistoryDayOut> {
    return this.http.get<HistoryDayOut>(`${this.base}/days/${day}`);
  }
}

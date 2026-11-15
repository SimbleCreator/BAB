import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ActivityIn, ActivityOut, ActivitySummaryOut, CsvImportOut, CsvPreviewOut } from './models';

/** Client for the backend `activity` router. */
@Injectable({ providedIn: 'root' })
export class ActivityApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/activity`;

  list(from: string, to: string): Observable<ActivityOut[]> {
    return this.http.get<ActivityOut[]>(this.base, { params: { from, to } });
  }

  summary(days: number): Observable<ActivitySummaryOut> {
    return this.http.get<ActivitySummaryOut>(`${this.base}/summary`, { params: { days } });
  }

  get(day: string): Observable<ActivityOut> {
    return this.http.get<ActivityOut>(`${this.base}/${day}`);
  }

  save(day: string, body: ActivityIn): Observable<ActivityOut> {
    return this.http.put<ActivityOut>(`${this.base}/${day}`, body);
  }

  delete(day: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${day}`);
  }

  templateUrl(): string {
    return `${this.base}/csv-template`;
  }

  previewCsv(file: File): Observable<CsvPreviewOut> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<CsvPreviewOut>(`${this.base}/import/preview`, form);
  }

  importCsv(file: File, overwrite: boolean): Observable<CsvImportOut> {
    const form = new FormData();
    form.append('file', file);
    form.append('overwrite', String(overwrite));
    return this.http.post<CsvImportOut>(`${this.base}/import`, form);
  }
}

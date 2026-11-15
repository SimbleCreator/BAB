import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { RunDetailOut, RunIn, RunListOut, RunPatch } from './models';

/** Client for the backend `runs` router. */
@Injectable({ providedIn: 'root' })
export class RunsApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/runs`;

  list(limit = 50, offset = 0): Observable<RunListOut> {
    return this.http.get<RunListOut>(this.base, { params: { limit, offset } });
  }

  get(id: number): Observable<RunDetailOut> {
    return this.http.get<RunDetailOut>(`${this.base}/${id}`);
  }

  create(body: RunIn): Observable<RunDetailOut> {
    return this.http.post<RunDetailOut>(this.base, body);
  }

  uploadGpx(file: File, note: string | null): Observable<RunDetailOut> {
    const form = new FormData();
    form.append('file', file);
    if (note) form.append('note', note);
    return this.http.post<RunDetailOut>(`${this.base}/gpx`, form);
  }

  update(id: number, body: RunPatch): Observable<RunDetailOut> {
    return this.http.patch<RunDetailOut>(`${this.base}/${id}`, body);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }
}

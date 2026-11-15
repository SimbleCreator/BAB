import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AdminStatsOut, DeleteAccountIn, PublicConfigOut } from './models';

/** Client for the backend `account` router (export, delete, public config, admin). */
@Injectable({ providedIn: 'root' })
export class AccountApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  /** The full export as a file body, ready to save. */
  export(): Observable<Blob> {
    return this.http.get(`${this.base}/account/export`, { responseType: 'blob' });
  }

  delete(body: DeleteAccountIn): Observable<void> {
    return this.http.post<void>(`${this.base}/account/delete`, body);
  }

  publicConfig(): Observable<PublicConfigOut> {
    return this.http.get<PublicConfigOut>(`${this.base}/config/public`);
  }

  adminStats(): Observable<AdminStatsOut> {
    return this.http.get<AdminStatsOut>(`${this.base}/admin/stats`);
  }
}

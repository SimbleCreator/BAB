import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { HealthOut } from './models';

/** Client for the backend `health` router. */
@Injectable({ providedIn: 'root' })
export class HealthApi {
  private readonly http = inject(HttpClient);

  check(): Observable<HealthOut> {
    return this.http.get<HealthOut>(`${environment.apiBaseUrl}/health`);
  }
}

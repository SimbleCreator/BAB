import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ProgressOut } from './models';

/** Client for the backend `progress` router. */
@Injectable({ providedIn: 'root' })
export class ProgressApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/progress`;

  get(): Observable<ProgressOut> {
    return this.http.get<ProgressOut>(this.base);
  }
}

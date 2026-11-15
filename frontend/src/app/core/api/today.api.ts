import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { TodayOut } from './models';

/** Client for the backend `today` router. */
@Injectable({ providedIn: 'root' })
export class TodayApi {
  private readonly http = inject(HttpClient);

  get(): Observable<TodayOut> {
    return this.http.get<TodayOut>(`${environment.apiBaseUrl}/today`);
  }
}

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { MilestoneOut } from './models';

/** Client for the backend `milestones` router. */
@Injectable({ providedIn: 'root' })
export class MilestonesApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/milestones`;

  list(): Observable<MilestoneOut[]> {
    return this.http.get<MilestoneOut[]>(this.base);
  }

  markSeen(): Observable<void> {
    return this.http.post<void>(`${this.base}/seen`, null);
  }
}

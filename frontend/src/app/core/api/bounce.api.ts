import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { BouncePlanOut, BounceStatusOut, GymProfileIn, GymProfileOut } from './models';

/** Client for the backend `bounce` router (the AI coach). */
@Injectable({ providedIn: 'root' })
export class BounceApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/bounce`;

  status(): Observable<BounceStatusOut> {
    return this.http.get<BounceStatusOut>(`${this.base}/status`);
  }

  /** 404 when Bounce has not made a plan yet. */
  plan(): Observable<BouncePlanOut> {
    return this.http.get<BouncePlanOut>(`${this.base}/plan`);
  }

  /** Asks the model for a new week. Can take up to a minute or more. */
  generate(): Observable<BouncePlanOut> {
    return this.http.post<BouncePlanOut>(`${this.base}/plan`, {});
  }

  /** 404 when no gym details are saved yet. */
  gymProfile(): Observable<GymProfileOut> {
    return this.http.get<GymProfileOut>(`${this.base}/gym-profile`);
  }

  saveGymProfile(body: GymProfileIn): Observable<GymProfileOut> {
    return this.http.put<GymProfileOut>(`${this.base}/gym-profile`, body);
  }
}

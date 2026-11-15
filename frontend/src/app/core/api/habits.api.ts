import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { DayLogOut, HabitIn, HabitOut, HabitStatusOut, WeekResultOut } from './models';

/** Client for the backend `habits` router (reduction plans). */
@Injectable({ providedIn: 'root' })
export class HabitsApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/habits`;

  list(): Observable<HabitStatusOut[]> {
    return this.http.get<HabitStatusOut[]>(this.base);
  }

  start(body: HabitIn): Observable<HabitStatusOut> {
    return this.http.post<HabitStatusOut>(this.base, body);
  }

  logOne(id: number): Observable<HabitStatusOut> {
    return this.http.post<HabitStatusOut>(`${this.base}/${id}/log`, {});
  }

  setDay(id: number, day: string, units: number): Observable<HabitStatusOut> {
    return this.http.put<HabitStatusOut>(`${this.base}/${id}/days/${day}`, { units });
  }

  days(id: number, from: string, to: string): Observable<DayLogOut[]> {
    return this.http.get<DayLogOut[]>(`${this.base}/${id}/days`, { params: { from, to } });
  }

  weeks(id: number): Observable<WeekResultOut[]> {
    return this.http.get<WeekResultOut[]>(`${this.base}/${id}/weeks`);
  }

  stop(id: number): Observable<HabitOut> {
    return this.http.post<HabitOut>(`${this.base}/${id}/stop`, {});
  }
}

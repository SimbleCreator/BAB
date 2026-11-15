import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, of, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ExerciseOut, WeekOut, WorkoutIn, WorkoutOut } from './models';

/** Client for the backend `training` router (plan, workouts and the exercise library). */
@Injectable({ providedIn: 'root' })
export class TrainingApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  week(day?: string): Observable<WeekOut> {
    const params: Record<string, string> = day ? { day } : {};
    return this.http.get<WeekOut>(`${this.base}/training/week`, { params });
  }

  /** The logged workout for a day, or null if nothing is logged. */
  workout(day: string): Observable<WorkoutOut | null> {
    return this.http
      .get<WorkoutOut>(`${this.base}/training/workouts/${day}`)
      .pipe(
        catchError((err: unknown) =>
          err instanceof HttpErrorResponse && err.status === 404 ? of(null) : throwError(() => err),
        ),
      );
  }

  saveWorkout(day: string, body: WorkoutIn): Observable<WorkoutOut> {
    return this.http.put<WorkoutOut>(`${this.base}/training/workouts/${day}`, body);
  }

  deleteWorkout(day: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/training/workouts/${day}`);
  }

  exercises(): Observable<ExerciseOut[]> {
    return this.http.get<ExerciseOut[]>(`${this.base}/exercises`);
  }

  exercise(code: string): Observable<ExerciseOut> {
    return this.http.get<ExerciseOut>(`${this.base}/exercises/${code}`);
  }
}

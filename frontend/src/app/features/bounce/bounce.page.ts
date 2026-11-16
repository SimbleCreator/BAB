import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';
import { Observable, catchError, of, throwError } from 'rxjs';

import { apiErrorCode, apiErrorMessage } from '../../core/api/api-error';
import { BounceApi } from '../../core/api/bounce.api';
import { BounceDay, BounceExercise, BouncePlanOut, GymProfileOut } from '../../core/api/models';
import { BounceBallComponent } from '../../shared/components/bounce-ball.component';
import { LoaderComponent } from '../../shared/components/loader.component';
import { shortDay } from '../../shared/format/dates';
import { GymFormComponent } from './gym-form.component';
import { LetterCardComponent } from './letter-card.component';
import { EXPERIENCE_OPTIONS, MODE_LABEL, SUPPLEMENT_OPTIONS } from './labels';

const DAYS: BounceDay[] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

/** A missing plan or gym profile is an empty state, not an error. */
function orNull<T>(source: Observable<T>): Observable<T | null> {
  return source.pipe(
    catchError((e: unknown) =>
      e instanceof HttpErrorResponse && e.status === 404 ? of(null) : throwError(() => e),
    ),
  );
}

function todayName(): BounceDay {
  return DAYS[(new Date().getDay() + 6) % 7];
}

@Component({
  selector: 'app-bounce-page',
  imports: [
    BounceBallComponent,
    LoaderComponent,
    MatButtonModule,
    MatIconModule,
    RouterLink,
    GymFormComponent,
    LetterCardComponent,
  ],
  templateUrl: './bounce.page.html',
  styleUrl: './bounce.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BouncePage {
  private readonly api = inject(BounceApi);

  protected readonly status = rxResource({ stream: () => this.api.status() });
  protected readonly plan = rxResource({ stream: () => orNull(this.api.plan()) });
  protected readonly gym = rxResource({ stream: () => orNull(this.api.gymProfile()) });

  protected readonly days = DAYS;
  protected readonly today = todayName();
  protected readonly selected = signal<BounceDay>(this.today);
  protected readonly generating = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly errorCode = signal<string | null>(null);
  protected readonly editingGym = signal(false);

  protected readonly modeLabel = computed(() => {
    const s = this.status.value();
    return s ? MODE_LABEL[s.mode] : '';
  });

  protected readonly planDay = computed(() => {
    const p = this.plan.value();
    return p?.content.days.find((d) => d.day === this.selected()) ?? null;
  });

  protected readonly mealDay = computed(() => {
    const p = this.plan.value();
    return p?.content.diet.days.find((d) => d.day === this.selected()) ?? null;
  });

  /** The gym form shows when Train is on and details are missing or being edited. */
  protected readonly showGymForm = computed(() => {
    const s = this.status.value();
    if (!s || s.mode === 'activity') return false;
    return this.editingGym() || (!this.gym.isLoading() && !this.gym.value());
  });

  protected readonly canGenerate = computed(() => !!this.status.value()?.can_generate);

  protected readonly generateLabel = computed(() => {
    const s = this.status.value();
    if (!s) return '';
    if (s.state === 'none' || !this.plan.value()) return 'Build my week';
    if (s.state === 'update_ready') return "Build next week's plan";
    return 'Rebuild with my new details';
  });

  protected generate(): void {
    this.generating.set(true);
    this.error.set(null);
    this.errorCode.set(null);
    this.api.generate().subscribe({
      next: (p: BouncePlanOut) => {
        this.generating.set(false);
        this.plan.set(p);
        this.selected.set(this.today);
        this.status.reload();
      },
      error: (e: unknown) => {
        this.generating.set(false);
        this.error.set(apiErrorMessage(e, 'Bounce could not build your plan. Try again.'));
        this.errorCode.set(apiErrorCode(e));
        this.status.reload();
      },
    });
  }

  protected gymSaved(g: GymProfileOut): void {
    this.gym.set(g);
    this.editingGym.set(false);
    this.status.reload();
  }

  protected dose(e: BounceExercise): string {
    const work = e.reps ? `${e.reps} reps` : e.seconds ? `${e.seconds}s` : '';
    const rest = e.rest_s ? ` · rest ${e.rest_s}s` : '';
    return `${e.sets} × ${work}${rest}`;
  }

  protected experienceLabel(v: string): string {
    return EXPERIENCE_OPTIONS.find((o) => o.value === v)?.label ?? v;
  }

  protected supplementLabels(codes: string[]): string {
    if (!codes.length) return 'None';
    return codes.map((c) => SUPPLEMENT_OPTIONS.find((o) => o.value === c)?.label ?? c).join(', ');
  }

  protected date(day: string): string {
    return shortDay(day);
  }
}

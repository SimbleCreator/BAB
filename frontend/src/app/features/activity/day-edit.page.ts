import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { provideNativeDateAdapter } from '@angular/material/core';
import { MatDatepicker, MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router, RouterLink } from '@angular/router';
import { catchError, map, of, throwError } from 'rxjs';

import { ActivityApi } from '../../core/api/activity.api';
import { apiErrorMessage } from '../../core/api/api-error';
import { ActivityIn, ActivityOut } from '../../core/api/models';
import { EstimateBadgeComponent } from '../../shared/components/estimate-badge.component';
import { dayLabel, formatDay, parseDay } from '../../shared/format/dates';
import { IntPipe, KmPipe } from '../../shared/format/format.pipes';

const atLeastOne = (group: AbstractControl): ValidationErrors | null => {
  const v = group.value as Record<string, unknown>;
  const has = (x: unknown) => x !== null && x !== undefined && x !== '';
  return has(v['steps']) || has(v['distance_km']) || has(v['active_kcal']) ? null : { empty: true };
};

@Component({
  selector: 'app-day-edit-page',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatDatepickerModule,
    MatProgressSpinnerModule,
    EstimateBadgeComponent,
    IntPipe,
    KmPipe,
  ],
  providers: [provideNativeDateAdapter()],
  templateUrl: './day-edit.page.html',
  styleUrl: './day-edit.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DayEditPage {
  private readonly api = inject(ActivityApi);
  private readonly router = inject(Router);
  private readonly snack = inject(MatSnackBar);

  /** Route parameter: YYYY-MM-DD. */
  readonly day = input.required<string>();
  /** Query `pick=1` opens the calendar straight away. */
  readonly pick = input<string>();
  /** Query `back`: where to go after saving. */
  readonly back = input<string>();

  private readonly picker = viewChild<MatDatepicker<Date>>('picker');

  protected readonly todayRes = rxResource({
    stream: () => this.api.summary(1).pipe(map((s) => s.today)),
  });
  protected readonly entry = rxResource({
    params: () => this.day(),
    stream: ({ params }) =>
      this.api
        .get(params)
        .pipe(
          catchError((err: unknown) =>
            err instanceof HttpErrorResponse && err.status === 404
              ? of(null as ActivityOut | null)
              : throwError(() => err),
          ),
        ),
  });

  protected readonly maxDate = computed(() => {
    const t = this.todayRes.value();
    return t ? parseDay(t) : new Date();
  });
  protected readonly dateValue = computed(() => parseDay(this.day()));
  protected readonly title = computed(() => {
    const t = this.todayRes.value();
    return t ? dayLabel(this.day(), t) : '';
  });
  protected readonly isFuture = computed(() => {
    const t = this.todayRes.value();
    return !!t && this.day() > t;
  });

  protected readonly form = inject(NonNullableFormBuilder).group(
    {
      steps: [null as number | null, [Validators.min(0), Validators.max(200000)]],
      distance_km: [null as number | null, [Validators.min(0), Validators.max(300)]],
      active_kcal: [null as number | null, [Validators.min(0), Validators.max(20000)]],
      note: ['', Validators.maxLength(500)],
    },
    { validators: atLeastOne },
  );
  protected readonly saving = signal(false);
  protected readonly confirmDelete = signal(false);
  protected readonly error = signal<string | null>(null);

  constructor() {
    effect(() => {
      const e = this.entry.value();
      if (e === undefined) return;
      this.confirmDelete.set(false);
      this.error.set(null);
      this.form.reset({
        steps: e?.steps ?? null,
        distance_km:
          e && !e.distance_estimated && e.distance_m !== null ? e.distance_m / 1000 : null,
        active_kcal: e && !e.active_kcal_estimated ? e.active_kcal : null,
        note: e?.note ?? '',
      });
    });
    effect(() => {
      const p = this.picker();
      if (p && this.pick() && this.todayRes.hasValue()) {
        queueMicrotask(() => p.open());
      }
    });
  }

  protected chooseDay(date: Date | null): void {
    if (!date) return;
    void this.router.navigate(['/activity/day', formatDay(date)], {
      queryParams: { back: this.back() ?? null },
      replaceUrl: true,
    });
  }

  protected save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    const num = (x: number | null) => (x === null || (x as unknown) === '' ? null : Number(x));
    const km = num(v.distance_km);
    const body: ActivityIn = {
      steps: num(v.steps) === null ? null : Math.round(num(v.steps)!),
      distance_m: km === null ? null : Math.round(km * 1000),
      active_kcal: num(v.active_kcal) === null ? null : Math.round(num(v.active_kcal)!),
      note: v.note.trim() || null,
    };
    this.saving.set(true);
    this.error.set(null);
    this.api.save(this.day(), body).subscribe({
      next: () => {
        this.snack.open('Saved.', undefined, { duration: 2000 });
        this.leave();
      },
      error: (err: unknown) => {
        this.saving.set(false);
        this.error.set(apiErrorMessage(err));
      },
    });
  }

  protected remove(): void {
    if (!this.confirmDelete()) {
      this.confirmDelete.set(true);
      return;
    }
    this.saving.set(true);
    this.api.delete(this.day()).subscribe({
      next: () => {
        this.snack.open('Day removed.', undefined, { duration: 2000 });
        this.leave();
      },
      error: (err: unknown) => {
        this.saving.set(false);
        this.error.set(apiErrorMessage(err));
      },
    });
  }

  private leave(): void {
    const back = this.back();
    const safe = back && back.startsWith('/') && !back.startsWith('//') ? back : '/activity';
    void this.router.navigateByUrl(safe);
  }
}

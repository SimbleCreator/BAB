import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { rxResource, takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { provideNativeDateAdapter } from '@angular/material/core';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { LowerCasePipe } from '@angular/common';

import { apiErrorMessage } from '../../core/api/api-error';
import { CheckinsApi } from '../../core/api/checkins.api';
import { AdjustmentOut, CheckinIn, CheckinOut } from '../../core/api/models';
import { WeightChartComponent } from '../../shared/components/weight-chart.component';
import { dayLabel, formatDay, parseDay } from '../../shared/format/dates';

const cm = [Validators.min(20), Validators.max(250)];

@Component({
  selector: 'app-checkin-page',
  imports: [
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatDatepickerModule,
    MatProgressSpinnerModule,
    WeightChartComponent,
    LowerCasePipe,
  ],
  providers: [provideNativeDateAdapter()],
  templateUrl: './checkin.page.html',
  styleUrl: './checkin.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CheckinPage {
  private readonly api = inject(CheckinsApi);
  private readonly snack = inject(MatSnackBar);

  protected readonly status = rxResource({ stream: () => this.api.status() });
  protected readonly history = rxResource({ stream: () => this.api.list() });
  protected readonly adjustments = rxResource({ stream: () => this.api.adjustments() });
  /** Result of the last save on this page: the adjustment it ran, or why none ran. */
  protected readonly justAdjusted = signal<AdjustmentOut | null>(null);
  protected readonly adjustmentNote = signal<string | null>(null);

  protected readonly form = inject(NonNullableFormBuilder).group({
    day: [new Date(), Validators.required],
    weight_kg: [
      null as number | null,
      [Validators.required, Validators.min(30), Validators.max(300)],
    ],
    waist_cm: [null as number | null, cm],
    chest_cm: [null as number | null, cm],
    arms_cm: [null as number | null, cm],
    thighs_cm: [null as number | null, cm],
    note: ['', Validators.maxLength(500)],
  });
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly confirmDelete = signal(false);
  /** The day currently in the form, as YYYY-MM-DD. */
  protected readonly formDay = signal<string | null>(null);

  protected readonly maxDate = computed(() => {
    const s = this.status.value();
    return s ? parseDay(s.today) : new Date();
  });
  protected readonly existing = computed(() => {
    const d = this.formDay();
    return this.history.value()?.find((c) => c.day === d) ?? null;
  });
  protected readonly chartPoints = computed(() => [...(this.history.value() ?? [])].reverse());

  constructor() {
    effect(() => {
      const s = this.status.value();
      if (s && this.formDay() === null) {
        this.form.controls.day.setValue(parseDay(s.today));
        this.formDay.set(s.today);
      }
    });
    this.form.controls.day.valueChanges.pipe(takeUntilDestroyed()).subscribe((d) => {
      if (d) this.formDay.set(formatDay(d));
    });
  }

  protected pct(v: number): string {
    return `${v > 0 ? '+' : ''}${v.toFixed(2)}%`;
  }

  protected label(day: string): string {
    const s = this.status.value();
    return s ? dayLabel(day, s.today) : day;
  }

  protected change(v: number | null, unit: string): string {
    if (v === null) return '';
    if (v === 0) return `no change`;
    return `${v > 0 ? '+' : ''}${v.toFixed(1)} ${unit}`;
  }

  /** "-0.8 kg · waist 86.5 cm (-1.5 cm)" */
  protected summary(c: CheckinOut): string {
    const parts: string[] = [];
    if (c.weight_change_kg !== null) parts.push(this.change(c.weight_change_kg, 'kg'));
    if (c.waist_cm !== null) {
      const waist = `waist ${c.waist_cm} cm`;
      parts.push(
        c.waist_change_cm !== null ? `${waist} (${this.change(c.waist_change_cm, 'cm')})` : waist,
      );
    }
    return parts.join(' · ');
  }

  protected edit(c: CheckinOut): void {
    this.confirmDelete.set(false);
    this.error.set(null);
    this.form.setValue({
      day: parseDay(c.day),
      weight_kg: c.weight_kg,
      waist_cm: c.waist_cm,
      chest_cm: c.chest_cm,
      arms_cm: c.arms_cm,
      thighs_cm: c.thighs_cm,
      note: c.note ?? '',
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  protected save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    const num = (x: number | null) => (x === null || (x as unknown) === '' ? null : Number(x));
    const body: CheckinIn = {
      weight_kg: Number(v.weight_kg),
      waist_cm: num(v.waist_cm),
      chest_cm: num(v.chest_cm),
      arms_cm: num(v.arms_cm),
      thighs_cm: num(v.thighs_cm),
      note: v.note.trim() || null,
    };
    this.saving.set(true);
    this.error.set(null);
    this.api.save(formatDay(v.day), body).subscribe({
      next: (saved) => {
        this.saving.set(false);
        this.justAdjusted.set(saved.adjustment);
        this.adjustmentNote.set(saved.adjustment_note);
        this.snack.open(
          saved.adjustment ? 'Check-in saved. Your plan was adjusted.' : 'Check-in saved.',
          undefined,
          { duration: 3000 },
        );
        this.status.reload();
        this.history.reload();
        this.adjustments.reload();
      },
      error: (err: unknown) => {
        this.saving.set(false);
        this.error.set(apiErrorMessage(err));
      },
    });
  }

  protected remove(): void {
    const day = this.formDay();
    if (!day) return;
    if (!this.confirmDelete()) {
      this.confirmDelete.set(true);
      return;
    }
    this.saving.set(true);
    this.api.delete(day).subscribe({
      next: () => {
        this.saving.set(false);
        this.confirmDelete.set(false);
        this.snack.open('Check-in removed.', undefined, { duration: 2000 });
        this.form.patchValue({
          weight_kg: null,
          waist_cm: null,
          chest_cm: null,
          arms_cm: null,
          thighs_cm: null,
          note: '',
        });
        this.status.reload();
        this.history.reload();
      },
      error: (err: unknown) => {
        this.saving.set(false);
        this.error.set(apiErrorMessage(err));
      },
    });
  }
}

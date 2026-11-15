import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { apiErrorMessage } from '../../core/api/api-error';
import { BounceApi } from '../../core/api/bounce.api';
import { GymExperience, GymProfileOut, SupplementCode } from '../../core/api/models';
import { EXPERIENCE_OPTIONS, SUPPLEMENT_OPTIONS } from './labels';

/** Gym experience, schedule and supplements: what Bounce asks before a Train plan. */
@Component({
  selector: 'app-gym-form',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatChipsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
  ],
  template: `
    <form [formGroup]="form" (ngSubmit)="save()" novalidate>
      <span class="label">Gym experience</span>
      <mat-button-toggle-group formControlName="experience" aria-label="Gym experience">
        @for (e of experiences; track e.value) {
          <mat-button-toggle [value]="e.value" [title]="e.hint">{{ e.label }}</mat-button-toggle>
        }
      </mat-button-toggle-group>
      @if (form.controls.experience.touched && form.controls.experience.invalid) {
        <p class="bab-field-error inline">Choose one.</p>
      }

      <div class="row">
        <mat-form-field>
          <mat-label>Gym days per week</mat-label>
          <mat-select formControlName="days_per_week">
            @for (d of dayOptions; track d) {
              <mat-option [value]="d">{{ d }}</mat-option>
            }
          </mat-select>
        </mat-form-field>
        <mat-form-field>
          <mat-label>Minutes per session</mat-label>
          <mat-select formControlName="session_minutes">
            @for (m of minuteOptions; track m) {
              <mat-option [value]="m">{{ m }} min</mat-option>
            }
          </mat-select>
        </mat-form-field>
      </div>

      <span class="label">Supplements you take now</span>
      <mat-chip-listbox
        multiple
        aria-label="Supplements"
        [value]="supplements()"
        (change)="pick($event.value)"
      >
        @for (s of supplementOptions; track s.value) {
          <mat-chip-option [value]="s.value">{{ s.label }}</mat-chip-option>
        }
      </mat-chip-listbox>
      <p class="hint">Bounce looks at what you take and tells you what it does and does not do.</p>

      <mat-form-field>
        <mat-label>Supplement details (optional)</mat-label>
        <textarea
          matInput
          formControlName="supplements_note"
          rows="2"
          maxlength="300"
          placeholder="Brand, dose, when you take it"
        ></textarea>
      </mat-form-field>
      <mat-form-field>
        <mat-label>Injuries or pain (optional)</mat-label>
        <textarea
          matInput
          formControlName="injuries_note"
          rows="2"
          maxlength="300"
          placeholder="For example: sore left knee"
        ></textarea>
      </mat-form-field>

      @if (error()) {
        <p class="bab-form-error" role="alert">{{ error() }}</p>
      }
      <button mat-flat-button type="submit" [disabled]="saving()">
        {{ saving() ? 'Saving...' : 'Save gym details' }}
      </button>
    </form>
  `,
  styles: `
    form {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .label {
      font-weight: 700;
      margin-top: 6px;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 10px;
    }
    .hint {
      margin: 0 0 8px;
      font-size: 0.85rem;
      color: var(--bab-text-dim);
    }
    mat-button-toggle-group {
      align-self: flex-start;
      flex-wrap: wrap;
    }
    @media (max-width: 400px) {
      .row {
        grid-template-columns: 1fr;
        gap: 0;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GymFormComponent {
  private readonly api = inject(BounceApi);

  readonly initial = input<GymProfileOut | null>(null);
  readonly saved = output<GymProfileOut>();

  protected readonly experiences = EXPERIENCE_OPTIONS;
  protected readonly supplementOptions = SUPPLEMENT_OPTIONS;
  protected readonly dayOptions = [1, 2, 3, 4, 5, 6, 7];
  protected readonly minuteOptions = [30, 45, 60, 75, 90, 120];

  protected readonly form = inject(NonNullableFormBuilder).group({
    experience: [null as GymExperience | null, Validators.required],
    days_per_week: [4, Validators.required],
    session_minutes: [60, Validators.required],
    supplements_note: ['', Validators.maxLength(300)],
    injuries_note: ['', Validators.maxLength(300)],
  });
  protected readonly supplements = signal<SupplementCode[]>([]);
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);

  constructor() {
    effect(() => {
      const g = this.initial();
      if (!g) return;
      this.form.setValue({
        experience: g.experience,
        days_per_week: g.days_per_week,
        session_minutes: g.session_minutes,
        supplements_note: g.supplements_note ?? '',
        injuries_note: g.injuries_note ?? '',
      });
      this.supplements.set(g.supplements);
    });
  }

  /** "None" and the other choices exclude each other. */
  protected pick(value: SupplementCode[]): void {
    const prev = this.supplements();
    const v = value ?? [];
    if (v.includes('none') && !prev.includes('none')) this.supplements.set(['none']);
    else this.supplements.set(v.filter((x) => x !== 'none'));
  }

  protected save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const f = this.form.getRawValue();
    this.saving.set(true);
    this.error.set(null);
    this.api
      .saveGymProfile({
        experience: f.experience!,
        days_per_week: f.days_per_week,
        session_minutes: f.session_minutes,
        supplements: this.supplements(),
        supplements_note: f.supplements_note.trim() || null,
        injuries_note: f.injuries_note.trim() || null,
      })
      .subscribe({
        next: (g) => {
          this.saving.set(false);
          this.saved.emit(g);
        },
        error: (e) => {
          this.saving.set(false);
          this.error.set(apiErrorMessage(e));
        },
      });
  }
}

import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';

import { apiErrorMessage } from '../../core/api/api-error';
import { HabitStatusOut, HabitType } from '../../core/api/models';
import { HabitsApi } from '../../core/api/habits.api';
import { HabitPlanComponent } from './habit-plan.component';
import { buildHabitForm, habitFromForm } from './habit-setup';
import { HabitSetupComponent } from './habit-setup.component';
import { PLAN_INTRO } from './wording';

@Component({
  selector: 'app-habits-page',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    HabitPlanComponent,
    HabitSetupComponent,
  ],
  template: `
    <section class="bab-page">
      <h1 class="bab-page-title">Habits</h1>
      @if (plans.isLoading() && !plans.hasValue()) {
        <div class="center"><mat-spinner diameter="40" /></div>
      } @else if (plans.error()) {
        <p class="bab-form-error">Could not load your plans.</p>
        <button mat-button type="button" (click)="plans.reload()">Try again</button>
      } @else {
        @for (p of plans.value() ?? []; track p.habit.id) {
          <app-habit-plan [status]="p" (changed)="onChanged(p, $event)" />
        }

        @if (freeTypes().length) {
          @if (!(plans.value() ?? []).length) {
            <p>{{ intro }}</p>
          }
          @if (!showSetup()) {
            <button mat-stroked-button type="button" (click)="openSetup()">
              <mat-icon>add</mat-icon>
              Start a reduction plan
            </button>
          } @else {
            <form [formGroup]="form" (ngSubmit)="startPlan()" novalidate class="setup">
              <app-habit-setup [form]="form" [showType]="freeTypes().length > 1" />
              <div class="actions">
                <button mat-flat-button type="submit" [disabled]="saving()">Start plan</button>
                <button mat-button type="button" (click)="showSetup.set(false)">Cancel</button>
              </div>
            </form>
          }
        }
        <p class="bab-disclaimer">
          General guidance, not medical advice. A doctor can help if you want to quit completely.
        </p>
      }
    </section>
  `,
  styles: `
    .center {
      display: flex;
      justify-content: center;
      padding: 48px;
    }
    .setup {
      padding: 16px;
      border-radius: 16px;
      border: 1px solid var(--mat-sys-outline-variant);
    }
    .actions {
      display: flex;
      gap: 8px;
      margin-top: 12px;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HabitsPage {
  private readonly api = inject(HabitsApi);
  private readonly snack = inject(MatSnackBar);

  protected readonly plans = rxResource({ stream: () => this.api.list() });
  protected readonly form = buildHabitForm(inject(NonNullableFormBuilder));
  protected readonly showSetup = signal(false);
  protected readonly saving = signal(false);
  protected readonly intro = PLAN_INTRO;

  protected readonly freeTypes = computed<HabitType[]>(() => {
    const used = new Set((this.plans.value() ?? []).map((p) => p.habit.type));
    return (['smoking', 'drinking'] as HabitType[]).filter((t) => !used.has(t));
  });

  protected openSetup(): void {
    this.form.reset({ type: this.freeTypes()[0], baseline: null, pace_pct: 5 });
    this.showSetup.set(true);
  }

  protected onChanged(old: HabitStatusOut, next: HabitStatusOut | null): void {
    this.plans.update((list) =>
      next
        ? (list ?? []).map((p) => (p.habit.id === old.habit.id ? next : p))
        : (list ?? []).filter((p) => p.habit.id !== old.habit.id),
    );
  }

  protected startPlan(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.api.start(habitFromForm(this.form)).subscribe({
      next: (s) => {
        this.saving.set(false);
        this.showSetup.set(false);
        this.plans.update((list) => [...(list ?? []), s]);
        this.snack.open('Plan started. Log honestly; the plan adjusts week by week.', undefined, {
          duration: 3000,
        });
      },
      error: (err: unknown) => {
        this.saving.set(false);
        this.snack.open(apiErrorMessage(err), undefined, { duration: 4000 });
      },
    });
  }
}

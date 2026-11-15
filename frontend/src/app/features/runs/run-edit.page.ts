import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  signal,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router, RouterLink } from '@angular/router';

import { apiErrorMessage } from '../../core/api/api-error';
import { RunsApi } from '../../core/api/runs.api';
import { TodayApi } from '../../core/api/today.api';
import { parseDay } from '../../shared/format/dates';
import { RunFieldsComponent } from './run-fields.component';
import { buildRunForm, patchRunForm, runFromForm } from './run-form';
import { LoaderComponent } from '../../shared/components/loader.component';

@Component({
  selector: 'app-run-edit-page',
  imports: [
    LoaderComponent,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    RunFieldsComponent,
  ],
  template: `
    <section class="bab-page">
      <a mat-button [routerLink]="['/runs', id()]" class="back">
        <mat-icon>arrow_back</mat-icon>
        Run
      </a>
      <h1 class="bab-page-title">Edit run</h1>
      @if (run.isLoading()) {
        <app-loader />
      } @else if (run.error()) {
        <p class="bab-form-error">Could not load this run.</p>
      } @else {
        @if (run.value()?.has_track) {
          <p class="bab-muted">
            The route map stays as recorded. Changing distance or time updates the totals, pace and
            splits.
          </p>
        }
        <form [formGroup]="form" (ngSubmit)="save()" novalidate>
          <app-run-fields [form]="form" [maxDate]="today()" />
          @if (error()) {
            <p class="bab-form-error" role="alert">{{ error() }}</p>
          }
          <button mat-flat-button type="submit" [disabled]="saving() || form.pristine">
            {{ saving() ? 'Saving...' : 'Save changes' }}
          </button>
        </form>
      }
    </section>
  `,
  styles: `
    .back {
      margin-left: -8px;
    }
    .center {
      display: flex;
      justify-content: center;
      padding: 48px;
    }
    button[type='submit'] {
      min-width: 160px;
      height: 48px;
      margin-top: 8px;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RunEditPage {
  private readonly api = inject(RunsApi);
  private readonly router = inject(Router);
  private readonly snack = inject(MatSnackBar);
  private readonly todayApi = inject(TodayApi);

  /** Route parameter. */
  readonly id = input.required<string>();

  protected readonly run = rxResource({
    params: () => Number(this.id()),
    stream: ({ params }) => this.api.get(params),
  });
  private readonly todayRes = rxResource({ stream: () => this.todayApi.get() });
  protected readonly today = computed(() => {
    const t = this.todayRes.value();
    return t ? parseDay(t.day) : new Date();
  });

  protected readonly form = buildRunForm(inject(NonNullableFormBuilder), new Date());
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);

  constructor() {
    effect(() => {
      const r = this.run.value();
      if (r) {
        patchRunForm(this.form, r);
        this.form.markAsPristine();
      }
    });
  }

  protected save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    const id = Number(this.id());
    this.api.update(id, runFromForm(this.form)).subscribe({
      next: () => {
        this.snack.open('Run updated.', undefined, { duration: 2000 });
        void this.router.navigate(['/runs', id], { replaceUrl: true });
      },
      error: (err: unknown) => {
        this.saving.set(false);
        this.error.set(apiErrorMessage(err));
      },
    });
  }
}

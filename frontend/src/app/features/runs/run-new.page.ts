import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { Router, RouterLink } from '@angular/router';

import { apiErrorMessage } from '../../core/api/api-error';
import { RunsApi } from '../../core/api/runs.api';
import { TodayApi } from '../../core/api/today.api';
import { parseDay } from '../../shared/format/dates';
import { RunFieldsComponent } from './run-fields.component';
import { buildRunForm, runFromForm } from './run-form';

const MAX_GPX_BYTES = 5 * 1024 * 1024;

@Component({
  selector: 'app-run-new-page',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatTabsModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressBarModule,
    RunFieldsComponent,
  ],
  templateUrl: './run-new.page.html',
  styleUrl: './run-new.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RunNewPage {
  private readonly api = inject(RunsApi);
  private readonly router = inject(Router);
  private readonly todayApi = inject(TodayApi);
  private readonly todayRes = rxResource({ stream: () => this.todayApi.get() });

  protected readonly today = computed(() => {
    const t = this.todayRes.value();
    return t ? parseDay(t.day) : new Date();
  });
  protected readonly form = buildRunForm(inject(NonNullableFormBuilder), new Date());
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly gpxFile = signal<File | null>(null);
  protected readonly gpxNote = signal('');
  protected readonly gpxError = signal<string | null>(null);

  constructor() {
    // Default the date to the user's "today" (profile timezone) once it is known.
    effect(() => {
      if (this.todayRes.hasValue() && this.form.controls.day.pristine) {
        this.form.controls.day.setValue(this.today());
      }
    });
  }

  protected saveManual(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    this.api.create(runFromForm(this.form)).subscribe({
      next: (run) => void this.router.navigate(['/runs', run.id], { replaceUrl: true }),
      error: (err: unknown) => {
        this.saving.set(false);
        this.error.set(apiErrorMessage(err));
      },
    });
  }

  protected chooseGpx(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    input.value = '';
    this.gpxError.set(null);
    if (file && file.size > MAX_GPX_BYTES) {
      this.gpxFile.set(null);
      this.gpxError.set('That file is larger than 5 MB.');
      return;
    }
    this.gpxFile.set(file);
  }

  protected uploadGpx(): void {
    const file = this.gpxFile();
    if (!file) return;
    this.saving.set(true);
    this.gpxError.set(null);
    this.api.uploadGpx(file, this.gpxNote().trim() || null).subscribe({
      next: (run) => void this.router.navigate(['/runs', run.id], { replaceUrl: true }),
      error: (err: unknown) => {
        this.saving.set(false);
        this.gpxError.set(apiErrorMessage(err));
      },
    });
  }
}

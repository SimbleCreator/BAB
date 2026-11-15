import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { RouterLink } from '@angular/router';

import { ActivityApi } from '../../core/api/activity.api';
import { apiErrorMessage } from '../../core/api/api-error';
import { CsvImportOut, CsvPreviewOut } from '../../core/api/models';
import { IntPipe, KmPipe } from '../../shared/format/format.pipes';

const MAX_BYTES = 1024 * 1024;

@Component({
  selector: 'app-import-page',
  imports: [
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatSlideToggleModule,
    IntPipe,
    KmPipe,
  ],
  templateUrl: './import.page.html',
  styleUrl: './import.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImportPage {
  private readonly api = inject(ActivityApi);

  protected readonly templateUrl = this.api.templateUrl();
  protected readonly file = signal<File | null>(null);
  protected readonly preview = signal<CsvPreviewOut | null>(null);
  protected readonly result = signal<CsvImportOut | null>(null);
  protected readonly overwrite = signal(false);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly importCount = computed(() => {
    const p = this.preview();
    if (!p) return 0;
    return this.overwrite() ? p.valid_rows : p.valid_rows - p.existing_rows;
  });

  protected readonly counts = computed(() => {
    const p = this.preview();
    if (!p) return '';
    const parts = [`${p.valid_rows} ready`, `${p.invalid_rows} with errors`];
    if (p.existing_rows) parts.push(`${p.existing_rows} already logged`);
    return parts.join(', ');
  });

  protected choose(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    input.value = '';
    this.reset();
    if (!file) return;
    if (file.size > MAX_BYTES) {
      this.error.set('That file is larger than 1 MB.');
      return;
    }
    this.file.set(file);
    this.busy.set(true);
    this.api.previewCsv(file).subscribe({
      next: (p) => {
        this.busy.set(false);
        this.preview.set(p);
      },
      error: (err: unknown) => {
        this.busy.set(false);
        this.error.set(apiErrorMessage(err));
      },
    });
  }

  protected runImport(): void {
    const file = this.file();
    if (!file) return;
    this.busy.set(true);
    this.error.set(null);
    this.api.importCsv(file, this.overwrite()).subscribe({
      next: (r) => {
        this.busy.set(false);
        this.result.set(r);
        this.preview.set(null);
      },
      error: (err: unknown) => {
        this.busy.set(false);
        this.error.set(apiErrorMessage(err));
      },
    });
  }

  protected reset(): void {
    this.file.set(null);
    this.preview.set(null);
    this.result.set(null);
    this.overwrite.set(false);
    this.error.set(null);
  }
}

import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

import { apiErrorMessage } from '../../core/api/api-error';
import { RunOut } from '../../core/api/models';
import { RunsApi } from '../../core/api/runs.api';
import { parseDay } from '../../shared/format/dates';
import { DurationPipe, KmPipe, PacePipe } from '../../shared/format/format.pipes';
import { LoaderComponent } from '../../shared/components/loader.component';

const PAGE = 20;
const DATE = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  year: 'numeric',
});

@Component({
  selector: 'app-runs-page',
  imports: [
    LoaderComponent,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    KmPipe,
    DurationPipe,
    PacePipe,
  ],
  templateUrl: './runs.page.html',
  styleUrl: './runs.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RunsPage {
  private readonly api = inject(RunsApi);

  protected readonly runs = signal<RunOut[]>([]);
  protected readonly total = signal(0);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly hasMore = computed(() => this.runs().length < this.total());

  constructor() {
    this.load();
  }

  protected dateLabel(day: string): string {
    return DATE.format(parseDay(day));
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.list(PAGE, this.runs().length).subscribe({
      next: (page) => {
        this.runs.update((r) => [...r, ...page.items]);
        this.total.set(page.total);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.error.set(apiErrorMessage(err, 'Could not load your runs.'));
      },
    });
  }
}

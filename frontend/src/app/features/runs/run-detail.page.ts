import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router, RouterLink } from '@angular/router';

import { apiErrorMessage } from '../../core/api/api-error';
import { RunsApi } from '../../core/api/runs.api';
import { EstimateBadgeComponent } from '../../shared/components/estimate-badge.component';
import { RouteMapComponent } from '../../shared/components/route-map.component';
import { parseDay } from '../../shared/format/dates';
import { DurationPipe, IntPipe, KmPipe, PacePipe } from '../../shared/format/format.pipes';

const DATE = new Intl.DateTimeFormat(undefined, {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
});
const TIME = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' });

@Component({
  selector: 'app-run-detail-page',
  imports: [
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    RouteMapComponent,
    EstimateBadgeComponent,
    KmPipe,
    DurationPipe,
    PacePipe,
    IntPipe,
  ],
  templateUrl: './run-detail.page.html',
  styleUrl: './run-detail.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RunDetailPage {
  private readonly api = inject(RunsApi);
  private readonly router = inject(Router);
  private readonly snack = inject(MatSnackBar);

  /** Route parameter. */
  readonly id = input.required<string>();

  protected readonly run = rxResource({
    params: () => Number(this.id()),
    stream: ({ params }) => this.api.get(params),
  });
  protected readonly confirmDelete = signal(false);
  protected readonly deleting = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly title = computed(() => {
    const r = this.run.value();
    return r ? DATE.format(parseDay(r.day)) : '';
  });
  protected readonly startTime = computed(() => {
    const r = this.run.value();
    return r?.started_at ? TIME.format(new Date(r.started_at)) : null;
  });
  protected readonly fastestKm = computed(() => {
    const full = (this.run.value()?.splits ?? []).filter((s) => s.distance_m === 1000);
    return full.length > 1 ? Math.min(...full.map((s) => s.pace_s_per_km)) : null;
  });

  protected remove(): void {
    if (!this.confirmDelete()) {
      this.confirmDelete.set(true);
      return;
    }
    this.deleting.set(true);
    this.api.delete(Number(this.id())).subscribe({
      next: () => {
        this.snack.open('Run deleted.', undefined, { duration: 2000 });
        void this.router.navigateByUrl('/runs', { replaceUrl: true });
      },
      error: (err: unknown) => {
        this.deleting.set(false);
        this.error.set(apiErrorMessage(err));
      },
    });
  }
}

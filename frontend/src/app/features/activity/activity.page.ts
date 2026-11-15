import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { RouterLink } from '@angular/router';

import { ActivityApi } from '../../core/api/activity.api';
import { StepsChartComponent } from '../../shared/components/steps-chart.component';
import { DayLabelPipe, IntPipe, KmPipe } from '../../shared/format/format.pipes';
import { LoaderComponent } from '../../shared/components/loader.component';

@Component({
  selector: 'app-activity-page',
  imports: [
    LoaderComponent,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatIconModule,
    MatListModule,
    StepsChartComponent,
    IntPipe,
    KmPipe,
    DayLabelPipe,
  ],
  templateUrl: './activity.page.html',
  styleUrl: './activity.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ActivityPage {
  private readonly api = inject(ActivityApi);

  protected readonly range = signal<7 | 30>(7);
  /** Always 30 days so the list below the chart has a month of entries. */
  protected readonly summary = rxResource({ stream: () => this.api.summary(30) });

  protected readonly chartDays = computed(() => {
    const days = this.summary.value()?.days ?? [];
    return days.slice(-this.range());
  });

  protected readonly todayPoint = computed(() => this.summary.value()?.days.at(-1) ?? null);

  protected readonly rangeTotals = computed(() => {
    const days = this.chartDays();
    const logged = days.filter((d) => d.has_entry);
    const steps = days.reduce((sum, d) => sum + d.steps, 0);
    return {
      steps,
      distance: days.reduce((sum, d) => sum + d.distance_m, 0),
      average: logged.length ? Math.round(steps / logged.length) : 0,
      goalDays: days.filter((d) => d.goal_met).length,
    };
  });

  protected readonly recent = computed(() =>
    (this.summary.value()?.days ?? []).filter((d) => d.has_entry).reverse(),
  );
}

import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { TodayApi } from '../../core/api/today.api';
import { EstimateBadgeComponent } from '../../shared/components/estimate-badge.component';
import { IntPipe, KmPipe } from '../../shared/format/format.pipes';
import { HABIT } from '../habits/wording';
import { mealForNow } from '../nutrition/meals';

@Component({
  selector: 'app-today-page',
  imports: [
    RouterLink,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    EstimateBadgeComponent,
    IntPipe,
    KmPipe,
  ],
  templateUrl: './today.page.html',
  styleUrl: './today.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TodayPage {
  private readonly api = inject(TodayApi);

  protected readonly today = rxResource({ stream: () => this.api.get() });

  protected readonly stepPercent = computed(() => {
    const t = this.today.value();
    if (!t?.activity?.steps) return 0;
    return Math.min(100, Math.round((t.activity.steps / t.step_goal) * 100));
  });

  protected readonly stepsLeft = computed(() => {
    const t = this.today.value();
    return t ? Math.max(0, t.step_goal - (t.activity?.steps ?? 0)) : 0;
  });

  protected readonly foodPercent = computed(() => {
    const n = this.today.value()?.nutrition;
    return n && n.target_kcal ? Math.min(100, Math.round((100 * n.eaten_kcal) / n.target_kcal)) : 0;
  });
  protected readonly mealNow = mealForNow;
  protected habitTitle(type: 'smoking' | 'drinking'): string {
    return HABIT[type].title;
  }

  protected readonly milestoneTitles = computed(() =>
    (this.today.value()?.new_milestones ?? []).map((m) => m.title).join(', '),
  );

  protected readonly dateLabel = computed(() => {
    const t = this.today.value();
    if (!t) return '';
    const [y, m, d] = t.day.split('-').map(Number);
    return new Intl.DateTimeFormat(undefined, {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    }).format(new Date(y, m - 1, d));
  });
}

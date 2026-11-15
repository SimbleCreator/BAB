import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router, RouterLink } from '@angular/router';
import { of } from 'rxjs';

import { HistoryApi } from '../../core/api/history.api';
import { MonthDayOut } from '../../core/api/models';
import { EstimateBadgeComponent } from '../../shared/components/estimate-badge.component';
import { dayLabel, parseDay } from '../../shared/format/dates';
import { DurationPipe, IntPipe, KmPipe } from '../../shared/format/format.pipes';
import { HABIT, units } from '../habits/wording';
import { MEAL_LABEL } from '../nutrition/meals';

const MONTH = new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' });
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split('-').map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

@Component({
  selector: 'app-history-page',
  imports: [
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    EstimateBadgeComponent,
    IntPipe,
    KmPipe,
    DurationPipe,
  ],
  templateUrl: './history.page.html',
  styleUrl: './history.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HistoryPage {
  private readonly api = inject(HistoryApi);
  private readonly router = inject(Router);

  /** Query parameters: month (YYYY-MM) and day (YYYY-MM-DD). */
  readonly month = input<string>();
  readonly day = input<string>();

  protected readonly data = rxResource({
    params: () => ({ month: this.month() }),
    stream: ({ params }) => this.api.month(params.month),
  });
  protected readonly selected = computed(() => {
    const m = this.data.value();
    if (!m) return null;
    const d = this.day();
    if (d && d.startsWith(m.month)) return d;
    return m.today.startsWith(m.month) ? m.today : null;
  });
  protected readonly detail = rxResource({
    params: () => ({ day: this.selected() }),
    stream: ({ params }) => (params.day ? this.api.day(params.day) : of(null)),
  });

  protected readonly weekdays = WEEKDAYS;
  protected readonly mealLabel = MEAL_LABEL;
  protected readonly habitWords = HABIT;
  protected readonly units = units;

  protected readonly title = computed(() => {
    const m = this.data.value();
    return m ? MONTH.format(parseDay(`${m.month}-01`)) : '';
  });
  protected readonly blanks = computed(() => {
    const m = this.data.value();
    return m ? Array.from({ length: (parseDay(m.days[0].day).getDay() + 6) % 7 }) : [];
  });
  protected readonly isCurrentMonth = computed(() => {
    const m = this.data.value();
    return !!m && m.today.startsWith(m.month);
  });

  protected dayNum(day: string): number {
    return Number(day.slice(8));
  }

  protected isFuture(d: MonthDayOut): boolean {
    return d.day > (this.data.value()?.today ?? '');
  }

  protected hasAny(d: MonthDayOut): boolean {
    return d.activity || !!d.workout || d.meals || d.checkin || d.runs > 0;
  }

  protected describe(d: MonthDayOut): string {
    const parts = [
      d.activity && 'activity',
      d.workout && `workout ${d.workout}`,
      d.meals && 'meals',
      d.checkin && 'check-in',
      d.runs && `${d.runs} run${d.runs > 1 ? 's' : ''}`,
    ].filter(Boolean);
    return `${dayLabel(d.day, this.data.value()?.today ?? '')}: ${parts.length ? parts.join(', ') : 'nothing logged'}`;
  }

  protected label(day: string): string {
    return dayLabel(day, this.data.value()?.today ?? day);
  }

  protected go(month: string | null, day: string | null): void {
    void this.router.navigate(['/history'], { queryParams: { month, day }, replaceUrl: true });
  }

  protected shift(delta: number): void {
    const m = this.data.value();
    if (!m) return;
    this.go(shiftMonth(m.month, delta), null);
  }

  protected pick(d: MonthDayOut): void {
    if (this.isFuture(d)) return;
    this.go(this.data.value()!.month, d.day);
  }
}

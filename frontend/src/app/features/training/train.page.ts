import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { RouterLink } from '@angular/router';
import { of } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-error';
import { DayStatus, PlanDayOut } from '../../core/api/models';
import { TrainingApi } from '../../core/api/training.api';
import { addDays, dayLabel, parseDay, weekday } from '../../shared/format/dates';
import { GROUP_LABEL, targetLine } from './format';
import { LoaderComponent } from '../../shared/components/loader.component';

const STATUS_LABEL: Record<DayStatus, string> = {
  rest: 'Rest',
  planned: 'Planned',
  not_logged: 'Not logged',
  done: 'Done',
  skipped: 'Skipped',
};
const DAY_NUM = new Intl.DateTimeFormat(undefined, { day: 'numeric' });

@Component({
  selector: 'app-train-page',
  imports: [LoaderComponent, RouterLink, MatCardModule, MatButtonModule, MatIconModule],
  templateUrl: './train.page.html',
  styleUrl: './train.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TrainPage {
  private readonly api = inject(TrainingApi);
  private readonly snack = inject(MatSnackBar);

  /** Any day inside the week being shown; null means this week. */
  protected readonly anchor = signal<string | undefined>(undefined);
  protected readonly selected = signal<string | null>(null);

  protected readonly week = rxResource({
    // Wrapped in an object: a resource whose params are `undefined` never loads.
    params: () => ({ day: this.anchor() }),
    stream: ({ params }) => this.api.week(params.day),
  });

  protected readonly day = computed<PlanDayOut | null>(() => {
    const w = this.week.value();
    if (!w) return null;
    const pick =
      this.selected() ?? (w.days.some((d) => d.day === w.today) ? w.today : w.days[0].day);
    return w.days.find((d) => d.day === pick) ?? w.days[0];
  });

  protected readonly log = rxResource({
    params: () => {
      const d = this.day();
      return d && (d.status === 'done' || d.status === 'skipped') ? d.day : null;
    },
    stream: ({ params }) => (params ? this.api.workout(params) : of(null)),
  });

  protected readonly isCurrentWeek = computed(() => {
    const w = this.week.value();
    return !!w && w.days.some((d) => d.day === w.today);
  });
  protected readonly busy = signal(false);

  protected readonly statusLabel = STATUS_LABEL;
  protected readonly groupLabel = GROUP_LABEL;
  protected readonly targetLine = targetLine;

  protected weekdayShort(day: string): string {
    return weekday(day);
  }

  protected dayNum(day: string): string {
    return DAY_NUM.format(parseDay(day));
  }

  protected label(day: string): string {
    const w = this.week.value();
    return w ? dayLabel(day, w.today) : day;
  }

  protected canLog(d: PlanDayOut): boolean {
    const w = this.week.value();
    return !!w && !!d.session && d.day <= w.today;
  }

  protected shiftWeek(delta: number): void {
    const w = this.week.value();
    if (!w) return;
    this.selected.set(null);
    this.anchor.set(addDays(w.week_start, delta * 7));
  }

  protected backToThisWeek(): void {
    this.selected.set(null);
    this.anchor.set(undefined);
  }

  protected skipDay(d: PlanDayOut): void {
    this.busy.set(true);
    this.api.saveWorkout(d.day, { status: 'skipped', sets: [] }).subscribe({
      next: () => this.afterChange('Marked as skipped. Rest up and go again next time.'),
      error: (err: unknown) => this.fail(err),
    });
  }

  protected clearLog(d: PlanDayOut): void {
    this.busy.set(true);
    this.api.deleteWorkout(d.day).subscribe({
      next: () => this.afterChange('Log cleared.'),
      error: (err: unknown) => this.fail(err),
    });
  }

  private afterChange(message: string): void {
    this.busy.set(false);
    this.snack.open(message, undefined, { duration: 2500 });
    this.week.reload();
  }

  private fail(err: unknown): void {
    this.busy.set(false);
    this.snack.open(apiErrorMessage(err), undefined, { duration: 4000 });
  }
}

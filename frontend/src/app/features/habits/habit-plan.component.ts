import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Observable, of } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-error';
import { HabitStatusOut } from '../../core/api/models';
import { HabitsApi } from '../../core/api/habits.api';
import { addDays, dayLabel, shortDay } from '../../shared/format/dates';
import { GOALS_LINE, HABIT, OVER_WEEK_LINE, ZERO_LINE, units } from './wording';

@Component({
  selector: 'app-habit-plan',
  imports: [MatButtonModule, MatIconModule, MatProgressBarModule],
  templateUrl: './habit-plan.component.html',
  styleUrl: './habit-plan.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HabitPlanComponent {
  private readonly api = inject(HabitsApi);
  private readonly snack = inject(MatSnackBar);

  readonly status = input.required<HabitStatusOut>();
  /** Emitted with the new status after any change, or null when the plan stops. */
  readonly changed = output<HabitStatusOut | null>();

  protected readonly words = HABIT;
  protected readonly goalsLine = GOALS_LINE;
  protected readonly overLine = OVER_WEEK_LINE;
  protected readonly zeroLine = ZERO_LINE;
  protected readonly units = units;
  protected readonly busy = signal(false);
  protected readonly showDays = signal(false);
  protected readonly confirmStop = signal(false);

  protected readonly w = computed(() => HABIT[this.status().habit.type]);
  protected readonly periodWord = computed(() =>
    this.status().availability.period === 'day' ? 'today' : 'this week',
  );

  /** The last 7 days of the plan (not before it started), newest first. */
  protected readonly recentDays = computed(() => {
    const s = this.status();
    const out: string[] = [];
    for (let i = 0; i < 7; i++) {
      const d = addDays(s.today, -i);
      if (d < s.habit.started_on) break;
      out.push(d);
    }
    return out;
  });
  protected readonly dayLog = rxResource({
    params: () => ({ open: this.showDays(), s: this.status() }),
    stream: ({ params }) => {
      if (!params.open) return of(null);
      const days = this.recentDays();
      return this.api.days(params.s.habit.id, days[days.length - 1], days[0]);
    },
  });
  protected readonly history = rxResource({
    params: () => ({ open: this.showDays(), id: this.status().habit.id }),
    stream: ({ params }) => (params.open ? this.api.weeks(params.id) : of(null)),
  });

  protected unitsOn(day: string): number {
    return this.dayLog.value()?.find((d) => d.day === day)?.units ?? 0;
  }

  protected label(day: string): string {
    return dayLabel(day, this.status().today);
  }

  protected range(start: string, end: string): string {
    return `${shortDay(start)} to ${shortDay(end)}`;
  }

  protected logOne(): void {
    this.run(this.api.logOne(this.status().habit.id), `Logged 1 ${this.w().unit}.`);
  }

  protected setDay(day: string, delta: number): void {
    const next = Math.max(0, this.unitsOn(day) + delta);
    this.run(this.api.setDay(this.status().habit.id, day, next), 'Updated.');
  }

  protected stop(): void {
    if (!this.confirmStop()) {
      this.confirmStop.set(true);
      return;
    }
    this.busy.set(true);
    this.api.stop(this.status().habit.id).subscribe({
      next: () => {
        this.busy.set(false);
        this.snack.open('Plan ended. You can start a new one any time.', undefined, {
          duration: 3000,
        });
        this.changed.emit(null);
      },
      error: (err: unknown) => this.fail(err),
    });
  }

  private run(obs: Observable<HabitStatusOut>, message: string): void {
    this.busy.set(true);
    obs.subscribe({
      next: (s) => {
        this.busy.set(false);
        this.changed.emit(s);
        this.dayLog.reload();
        this.snack.open(message, undefined, { duration: 1500 });
      },
      error: (err: unknown) => this.fail(err),
    });
  }

  private fail(err: unknown): void {
    this.busy.set(false);
    this.snack.open(apiErrorMessage(err), undefined, { duration: 4000 });
  }
}

import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { RouterLink } from '@angular/router';

import { ActivityApi } from '../../core/api/activity.api';
import { apiErrorMessage } from '../../core/api/api-error';
import { LoaderComponent } from '../../shared/components/loader.component';

/** "Easy day": a 10-minute plan for rough days that keeps the streak alive. */
@Component({
  selector: 'app-easy-day-page',
  imports: [MatButtonModule, MatIconModule, RouterLink, LoaderComponent],
  templateUrl: './easy-day.page.html',
  styleUrl: './easy-day.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EasyDayPage {
  private readonly api = inject(ActivityApi);
  private readonly snack = inject(MatSnackBar);

  protected readonly data = rxResource({ stream: () => this.api.easyDay() });
  protected readonly busy = signal(false);

  /** The guided timer: index of the current move, seconds left, running or not. */
  protected readonly step = signal<number | null>(null);
  protected readonly left = signal(0);
  protected readonly running = signal(false);
  protected readonly done = signal(false);
  private timer: ReturnType<typeof setInterval> | null = null;

  protected readonly current = computed(() => {
    const i = this.step();
    const plan = this.data.value()?.plan ?? [];
    return i === null ? null : (plan[i] ?? null);
  });

  constructor() {
    inject(DestroyRef).onDestroy(() => this.stopTimer());
  }

  protected take(): void {
    this.busy.set(true);
    this.api.takeEasyDay().subscribe({
      next: (d) => {
        this.busy.set(false);
        this.data.set(d);
        this.snack.open('Easy day on. Your streak is safe.', undefined, { duration: 2500 });
      },
      error: (err: unknown) => {
        this.busy.set(false);
        this.snack.open(apiErrorMessage(err), undefined, { duration: 4000 });
      },
    });
  }

  protected undo(): void {
    this.busy.set(true);
    this.api.undoEasyDay().subscribe({
      next: (d) => {
        this.busy.set(false);
        this.data.set(d);
        this.reset();
      },
      error: (err: unknown) => {
        this.busy.set(false);
        this.snack.open(apiErrorMessage(err), undefined, { duration: 4000 });
      },
    });
  }

  protected start(): void {
    this.done.set(false);
    this.goTo(0);
  }

  protected toggle(): void {
    if (this.running()) this.stopTimer();
    else this.runTimer();
  }

  protected next(): void {
    const i = this.step();
    if (i === null) return;
    this.goTo(i + 1);
  }

  protected reset(): void {
    this.stopTimer();
    this.step.set(null);
    this.done.set(false);
  }

  protected clock(s: number): string {
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  }

  protected mins(s: number): string {
    return s % 60 ? `${Math.floor(s / 60)} min ${s % 60} s` : `${s / 60} min`;
  }

  private goTo(i: number): void {
    const plan = this.data.value()?.plan ?? [];
    this.stopTimer();
    if (i >= plan.length) {
      this.step.set(null);
      this.done.set(true);
      return;
    }
    this.step.set(i);
    this.left.set(plan[i].seconds);
    this.runTimer();
  }

  private runTimer(): void {
    this.stopTimer();
    this.running.set(true);
    this.timer = setInterval(() => {
      const s = this.left() - 1;
      if (s <= 0) this.next();
      else this.left.set(s);
    }, 1000);
  }

  private stopTimer(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    this.running.set(false);
  }
}

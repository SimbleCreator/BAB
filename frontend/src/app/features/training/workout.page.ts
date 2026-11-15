import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  effect,
  inject,
  input,
  signal,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { apiErrorMessage } from '../../core/api/api-error';
import { PrescriptionOut, SetIn, WorkoutOut } from '../../core/api/models';
import { TrainingApi } from '../../core/api/training.api';
import { dayLabel } from '../../shared/format/dates';
import { formatDuration } from '../../shared/format/format.pipes';
import { targetLine } from './format';

interface Entry {
  value: number | null;
  done: boolean;
}

const key = (code: string, n: number) => `${code}#${n}`;

@Component({
  selector: 'app-workout-page',
  imports: [
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './workout.page.html',
  styleUrl: './workout.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkoutPage {
  private readonly api = inject(TrainingApi);

  /** Route parameter: YYYY-MM-DD. */
  readonly day = input.required<string>();

  protected readonly week = rxResource({
    params: () => this.day(),
    stream: ({ params }) => this.api.week(params),
  });
  protected readonly existing = rxResource({
    params: () => this.day(),
    stream: ({ params }) => this.api.workout(params),
  });

  protected readonly session = computed(
    () => this.week.value()?.days.find((d) => d.day === this.day())?.session ?? null,
  );
  protected readonly items = computed<PrescriptionOut[]>(() => {
    const s = this.session();
    return s ? [...s.exercises, ...(s.finisher ? [s.finisher] : [])] : [];
  });
  protected readonly title = computed(() => {
    const w = this.week.value();
    return w ? dayLabel(this.day(), w.today) : '';
  });

  protected readonly entries = signal<Record<string, Entry>>({});
  protected readonly skipped = signal<Set<string>>(new Set());
  protected readonly openInfo = signal<string | null>(null);
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly result = signal<WorkoutOut | null>(null);

  protected readonly progress = computed(() => {
    const all = this.items().reduce((n, p) => n + p.sets, 0);
    const done = Object.values(this.entries()).filter((e) => e.done).length;
    return { done, all, pct: all ? Math.round((100 * done) / all) : 0 };
  });

  // Rest timer and timed-set countdown share one ticking interval.
  protected readonly rest = signal<{ left: number; total: number } | null>(null);
  protected readonly countdown = signal<{ key: string; left: number } | null>(null);
  private ticker: ReturnType<typeof setInterval> | null = null;
  private initialised = false;

  protected readonly targetLine = targetLine;
  protected readonly formatDuration = formatDuration;

  constructor() {
    inject(DestroyRef).onDestroy(() => this.stopTicker());
    effect(() => {
      const items = this.items();
      if (this.initialised || !items.length || this.existing.isLoading()) return;
      const log = this.existing.value();
      const next: Record<string, Entry> = {};
      for (const p of items) {
        for (let n = 1; n <= p.sets; n++) {
          const logged = log?.sets.find((s) => s.exercise_code === p.code && s.set_no === n);
          const actual = logged ? (logged.actual_reps ?? logged.actual_seconds) : null;
          next[key(p.code, n)] = {
            value: actual ?? this.target(p),
            done: actual !== null && actual !== undefined,
          };
        }
      }
      this.entries.set(next);
      this.initialised = true;
    });
  }

  protected target(p: PrescriptionOut): number {
    return (p.target_seconds ?? p.target_reps) || 0;
  }

  protected setNumbers(p: PrescriptionOut): number[] {
    return Array.from({ length: p.sets }, (_, i) => i + 1);
  }

  protected entry(code: string, n: number): Entry {
    return this.entries()[key(code, n)] ?? { value: null, done: false };
  }

  protected setValue(code: string, n: number, raw: string): void {
    const v = raw === '' ? null : Math.max(0, Math.round(Number(raw)));
    this.entries.update((e) => ({ ...e, [key(code, n)]: { ...e[key(code, n)], value: v } }));
  }

  protected toggleDone(p: PrescriptionOut, n: number): void {
    const k = key(p.code, n);
    const wasDone = this.entries()[k]?.done;
    this.entries.update((e) => ({
      ...e,
      [k]: { value: e[k]?.value ?? this.target(p), done: !wasDone },
    }));
    if (!wasDone) {
      this.unskip(p.code);
      this.startRest(p.rest_s);
    }
  }

  protected startCountdown(p: PrescriptionOut, n: number): void {
    this.rest.set(null);
    this.countdown.set({ key: key(p.code, n), left: this.target(p) });
    this.ensureTicker();
  }

  protected isCounting(code: string, n: number): boolean {
    return this.countdown()?.key === key(code, n);
  }

  protected skipExercise(code: string): void {
    this.skipped.update((s) => new Set(s).add(code));
    this.entries.update((e) => {
      const next = { ...e };
      for (const k of Object.keys(next)) {
        if (k.startsWith(code + '#')) next[k] = { ...next[k], done: false };
      }
      return next;
    });
  }

  protected unskip(code: string): void {
    if (!this.skipped().has(code)) return;
    this.skipped.update((s) => {
      const n = new Set(s);
      n.delete(code);
      return n;
    });
  }

  protected startRest(seconds: number): void {
    this.countdown.set(null);
    this.rest.set({ left: seconds, total: seconds });
    this.ensureTicker();
  }

  protected addRest(seconds: number): void {
    this.rest.update((r) => (r ? { left: r.left + seconds, total: r.total + seconds } : r));
  }

  protected skipRest(): void {
    this.rest.set(null);
  }

  protected finish(): void {
    const sets: SetIn[] = [];
    for (const p of this.items()) {
      for (let n = 1; n <= p.sets; n++) {
        const e = this.entry(p.code, n);
        if (!e.done || e.value === null) continue;
        sets.push({
          exercise_code: p.code,
          set_no: n,
          actual_reps: p.type === 'reps' ? e.value : null,
          actual_seconds: p.type === 'timed' ? e.value : null,
        });
      }
    }
    this.saving.set(true);
    this.error.set(null);
    this.stopTicker();
    this.api.saveWorkout(this.day(), { status: 'done', sets }).subscribe({
      next: (r) => {
        this.saving.set(false);
        this.result.set(r);
        window.scrollTo({ top: 0 });
      },
      error: (err: unknown) => {
        this.saving.set(false);
        this.error.set(apiErrorMessage(err));
      },
    });
  }

  private ensureTicker(): void {
    if (this.ticker) return;
    this.ticker = setInterval(() => this.tick(), 1000);
  }

  private stopTicker(): void {
    if (this.ticker) clearInterval(this.ticker);
    this.ticker = null;
    this.rest.set(null);
    this.countdown.set(null);
  }

  private tick(): void {
    const c = this.countdown();
    if (c) {
      if (c.left <= 1) {
        this.countdown.set(null);
        this.entries.update((e) => ({
          ...e,
          [c.key]: { value: e[c.key]?.value ?? 0, done: true },
        }));
        const [code] = c.key.split('#');
        const p = this.items().find((x) => x.code === code);
        this.buzz();
        if (p) this.startRest(p.rest_s);
      } else {
        this.countdown.set({ ...c, left: c.left - 1 });
      }
      return;
    }
    const r = this.rest();
    if (r) {
      if (r.left <= 1) {
        this.rest.set(null);
        this.buzz();
      } else {
        this.rest.set({ ...r, left: r.left - 1 });
      }
      return;
    }
    if (this.ticker) clearInterval(this.ticker);
    this.ticker = null;
  }

  private buzz(): void {
    if ('vibrate' in navigator) navigator.vibrate?.(200);
  }

  protected readonly hasLog = computed(() => this.existing.value() !== null);
  protected readonly weekReady = computed(() => this.week.hasValue());
  protected readonly todayIso = computed(() => this.week.value()?.today ?? '');
  protected readonly isFuture = computed(() => !!this.todayIso() && this.day() > this.todayIso());
  protected readonly noSession = computed(() => this.weekReady() && !this.session());
  protected readonly ready = computed(() => this.weekReady() && !this.existing.isLoading());
}

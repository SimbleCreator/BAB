import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AccountApi } from '../../core/api/account.api';
import { shortDay } from '../../shared/format/dates';
import { IntPipe } from '../../shared/format/format.pipes';

const RECORD_LABEL: Record<string, string> = {
  daily_activity: 'Activity days',
  runs: 'Runs',
  workouts: 'Workouts',
  meals: 'Meals',
  meal_items: 'Meal items',
  custom_foods: 'Custom foods',
  checkins: 'Check-ins',
  milestones: 'Milestones unlocked',
  habits: 'Reduction plans',
  habit_logs: 'Reduction plan logs',
};

@Component({
  selector: 'app-admin-page',
  imports: [MatCardModule, MatButtonModule, MatProgressSpinnerModule, IntPipe],
  template: `
    <section class="bab-page">
      <h1 class="bab-page-title">Admin</h1>
      <p class="bab-muted">Totals only. No one's personal data is shown here.</p>
      @if (stats.isLoading()) {
        <div class="center"><mat-spinner diameter="40" /></div>
      } @else if (stats.error()) {
        <p class="bab-form-error">Could not load the numbers.</p>
        <button mat-button type="button" (click)="stats.reload()">Try again</button>
      } @else if (stats.value(); as s) {
        <div class="tiles">
          <div class="tile">
            <div class="bab-stat">{{ s.total_users | int }}</div>
            <div class="bab-muted">users</div>
          </div>
          <div class="tile">
            <div class="bab-stat">{{ s.active_7_days | int }}</div>
            <div class="bab-muted">active, 7 days</div>
          </div>
          <div class="tile">
            <div class="bab-stat">{{ s.active_30_days | int }}</div>
            <div class="bab-muted">active, 30 days</div>
          </div>
        </div>
        <mat-card appearance="outlined">
          <mat-card-header><mat-card-title>New users per week</mat-card-title></mat-card-header>
          <mat-card-content>
            @for (w of s.new_users_per_week; track w.week_start) {
              <div class="bar-row">
                <span class="wk">{{ label(w.week_start) }}</span>
                <span class="bar"><span [style.width.%]="pct(w.count)"></span></span>
                <span class="n">{{ w.count }}</span>
              </div>
            }
          </mat-card-content>
        </mat-card>
        <mat-card appearance="outlined">
          <mat-card-header><mat-card-title>Records</mat-card-title></mat-card-header>
          <mat-card-content>
            @for (r of records(); track r.key) {
              <div class="rec">
                <span>{{ r.label }}</span
                ><span>{{ r.count | int }}</span>
              </div>
            }
          </mat-card-content>
        </mat-card>
      }
    </section>
  `,
  styles: `
    .center {
      display: flex;
      justify-content: center;
      padding: 32px;
    }
    .tiles {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-bottom: 16px;
    }
    .tile {
      padding: 12px;
      border-radius: 12px;
      background: var(--mat-sys-surface-container);
    }
    .tile .bab-stat {
      font: var(--mat-sys-headline-medium);
    }
    mat-card {
      margin-bottom: 16px;
    }
    .bar-row {
      display: grid;
      grid-template-columns: 64px 1fr 32px;
      gap: 8px;
      align-items: center;
      padding: 3px 0;
    }
    .wk {
      font: var(--mat-sys-label-medium);
      color: var(--mat-sys-on-surface-variant);
    }
    .bar {
      height: 10px;
      border-radius: 5px;
      background: var(--mat-sys-surface-container-high);
      overflow: hidden;
    }
    .bar span {
      display: block;
      height: 100%;
      background: var(--mat-sys-primary);
    }
    .n {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .rec {
      display: flex;
      justify-content: space-between;
      padding: 6px 0;
      border-bottom: 1px solid var(--mat-sys-outline-variant);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminPage {
  private readonly api = inject(AccountApi);
  protected readonly stats = rxResource({ stream: () => this.api.adminStats() });
  private readonly max = computed(() =>
    Math.max(1, ...(this.stats.value()?.new_users_per_week.map((w) => w.count) ?? [1])),
  );
  protected readonly records = computed(() =>
    Object.entries(this.stats.value()?.records ?? {}).map(([key, count]) => ({
      key,
      count,
      label: RECORD_LABEL[key] ?? key,
    })),
  );

  protected pct(n: number): number {
    return (100 * n) / this.max();
  }

  protected label(day: string): string {
    return shortDay(day);
  }
}

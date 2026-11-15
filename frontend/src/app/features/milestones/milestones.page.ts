import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { MilestoneCategory, MilestoneOut } from '../../core/api/models';
import { MilestonesApi } from '../../core/api/milestones.api';

const GROUPS: { category: MilestoneCategory; label: string; icon: string }[] = [
  { category: 'steps', label: 'Steps', icon: 'directions_walk' },
  { category: 'runs', label: 'Runs', icon: 'directions_run' },
  { category: 'training', label: 'Training', icon: 'fitness_center' },
  { category: 'food', label: 'Food', icon: 'restaurant' },
  { category: 'checkins', label: 'Check-ins', icon: 'monitor_weight' },
  { category: 'habits', label: 'Habits', icon: 'trending_down' },
];

const INT = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
const KM = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
const DATE = new Intl.DateTimeFormat(undefined, {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
});

@Component({
  selector: 'app-milestones-page',
  imports: [MatIconModule, MatButtonModule, MatProgressBarModule, MatProgressSpinnerModule],
  templateUrl: './milestones.page.html',
  styleUrl: './milestones.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MilestonesPage {
  private readonly api = inject(MilestonesApi);

  protected readonly milestones = rxResource({ stream: () => this.api.list() });
  /** Unlocks to celebrate, captured once before they are marked as seen. */
  protected readonly celebrate = signal<MilestoneOut[]>([]);
  private marked = false;

  protected readonly groups = computed(() => {
    const all = this.milestones.value() ?? [];
    return GROUPS.map((g) => ({
      ...g,
      items: all.filter((m) => m.category === g.category),
    })).filter((g) => g.items.length);
  });
  protected readonly unlockedCount = computed(
    () => (this.milestones.value() ?? []).filter((m) => m.unlocked_at).length,
  );
  protected readonly total = computed(() => this.milestones.value()?.length ?? 0);

  constructor() {
    effect(() => {
      const all = this.milestones.value();
      if (!all || this.marked) return;
      const fresh = all.filter((m) => m.unlocked_at && !m.seen);
      if (fresh.length) {
        this.marked = true;
        this.celebrate.set(fresh);
        this.api.markSeen().subscribe();
      }
    });
  }

  protected percent(m: MilestoneOut): number {
    return Math.min(100, Math.round((m.current / m.target) * 100));
  }

  protected progressText(m: MilestoneOut): string {
    switch (m.unit) {
      case 'm':
        return `${KM.format(m.current / 1000)} / ${KM.format(m.target / 1000)} km`;
      case 'steps':
        return `${INT.format(m.current)} / ${INT.format(m.target)} steps`;
      case 'days':
        return `${m.current} / ${m.target} days`;
      case 'weeks':
        return `${m.current} / ${m.target} ${m.target === 1 ? 'week' : 'weeks'}`;
      default:
        return `${m.current} / ${m.target}`;
    }
  }

  protected unlockedOn(m: MilestoneOut): string {
    return m.unlocked_at ? DATE.format(new Date(m.unlocked_at)) : '';
  }

  protected isFresh(m: MilestoneOut): boolean {
    return this.celebrate().some((c) => c.code === m.code);
  }
}

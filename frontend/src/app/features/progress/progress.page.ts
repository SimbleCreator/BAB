import { ChangeDetectionStrategy, Component, computed, effect, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

import { BlockOut, ChangeOut } from '../../core/api/models';
import { ProgressApi } from '../../core/api/progress.api';
import { EstimateBadgeComponent } from '../../shared/components/estimate-badge.component';
import { LoaderComponent } from '../../shared/components/loader.component';
import { parseDay } from '../../shared/format/dates';
import { markCardSeen } from './seen-card';
import { kg, projectionText } from './projection-text';

const DAY = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' });
const INT = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

const NAMES: Record<string, { label: string; unit: string }> = {
  weight_kg: { label: 'Weight', unit: 'kg' },
  waist_cm: { label: 'Waist', unit: 'cm' },
  chest_cm: { label: 'Chest', unit: 'cm' },
  arms_cm: { label: 'Arms', unit: 'cm' },
  thighs_cm: { label: 'Thighs', unit: 'cm' },
  energy: { label: 'Energy', unit: '/5' },
  sleep: { label: 'Sleep', unit: '/5' },
  stairs: { label: 'Stairs', unit: '/5' },
};

@Component({
  selector: 'app-progress-page',
  imports: [RouterLink, MatButtonModule, MatIconModule, LoaderComponent, EstimateBadgeComponent],
  templateUrl: './progress.page.html',
  styleUrl: './progress.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProgressPage {
  private readonly api = inject(ProgressApi);

  protected readonly data = rxResource({ stream: () => this.api.get() });
  protected readonly text = computed(() => {
    const d = this.data.value();
    return d ? projectionText(d.projection) : null;
  });

  constructor() {
    effect(() => {
      const newest = this.data.value()?.cards[0];
      if (newest) markCardSeen(newest.number);
    });
  }

  protected kg = kg;

  protected range(start: string, end: string): string {
    return `${DAY.format(parseDay(start))} to ${DAY.format(parseDay(end))}`;
  }

  protected day(d: string): string {
    return DAY.format(parseDay(d));
  }

  protected label(c: ChangeOut): string {
    return NAMES[c.name]?.label ?? c.name;
  }

  protected value(c: ChangeOut, v: number): string {
    const unit = NAMES[c.name]?.unit ?? '';
    return unit.startsWith('/') ? `${v}${unit}` : `${v} ${unit}`;
  }

  protected delta(c: ChangeOut): string {
    if (c.change === 0) return 'same';
    const unit = NAMES[c.name]?.unit ?? '';
    const sign = c.change > 0 ? '+' : '−';
    return `${sign}${Math.abs(c.change)}${unit.startsWith('/') ? '' : ' ' + unit}`;
  }

  protected steps(b: BlockOut | null): string {
    return b?.avg_steps != null ? INT.format(b.avg_steps) : '–';
  }
}

import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  afterRenderEffect,
  input,
  viewChild,
} from '@angular/core';
import {
  CategoryScale,
  Chart,
  Filler,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';

import { shortDay } from '../format/dates';

Chart.register(
  CategoryScale,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
  Filler,
);

export interface WeightPoint {
  day: string;
  weight_kg: number;
}

function cssVar(name: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

/** Weight over time, oldest on the left. */
@Component({
  selector: 'app-weight-chart',
  template: '<div class="wrap"><canvas #canvas aria-label="Weight trend"></canvas></div>',
  styles: `
    .wrap {
      position: relative;
      height: 200px;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WeightChartComponent implements OnDestroy {
  /** Oldest first. */
  readonly points = input.required<WeightPoint[]>();

  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private chart: Chart | null = null;

  constructor() {
    afterRenderEffect(() => this.draw(this.points()));
  }

  ngOnDestroy(): void {
    this.chart?.destroy();
  }

  private draw(points: WeightPoint[]): void {
    const primary = cssVar('--mat-sys-primary', '#ffb59d');
    const text = cssVar('--mat-sys-on-surface-variant', '#d8c2bb');
    const grid = cssVar('--mat-sys-outline-variant', '#53433f');
    this.chart?.destroy();
    this.chart = new Chart(this.canvas().nativeElement, {
      type: 'line',
      data: {
        labels: points.map((p) => shortDay(p.day)),
        datasets: [
          {
            label: 'Weight (kg)',
            data: points.map((p) => p.weight_kg),
            borderColor: primary,
            backgroundColor: primary + '22',
            fill: true,
            tension: 0.25,
            pointRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: text, maxTicksLimit: 6, maxRotation: 0 }, grid: { display: false } },
          y: { ticks: { color: text }, grid: { color: grid } },
        },
      },
    });
  }
}

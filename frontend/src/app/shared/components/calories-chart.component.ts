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
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';

import { NutritionDayPoint } from '../../core/api/models';
import { weekday } from '../format/dates';

Chart.register(
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
);

function cssVar(name: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

/** Calories eaten per day as bars, with the day's target as a dashed line. */
@Component({
  selector: 'app-calories-chart',
  template: '<div class="wrap"><canvas #canvas aria-label="Calories per day"></canvas></div>',
  styles: `
    .wrap {
      position: relative;
      height: 200px;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CaloriesChartComponent implements OnDestroy {
  readonly days = input.required<NutritionDayPoint[]>();
  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private chart: Chart | null = null;

  constructor() {
    afterRenderEffect(() => this.draw(this.days()));
  }

  ngOnDestroy(): void {
    this.chart?.destroy();
  }

  private draw(days: NutritionDayPoint[]): void {
    const primary = cssVar('--mat-sys-primary', '#ffb59d');
    const over = cssVar('--mat-sys-tertiary', '#d6c68e');
    const text = cssVar('--mat-sys-on-surface-variant', '#d8c2bb');
    const grid = cssVar('--mat-sys-outline-variant', '#53433f');
    this.chart?.destroy();
    this.chart = new Chart(this.canvas().nativeElement, {
      data: {
        labels: days.map((d) => weekday(d.day)),
        datasets: [
          {
            type: 'bar',
            label: 'Eaten (kcal)',
            data: days.map((d) => d.calories_kcal),
            backgroundColor: days.map((d) => (d.calories_kcal > d.target_kcal ? over : primary)),
            borderRadius: 4,
            maxBarThickness: 36,
          },
          {
            type: 'line',
            label: 'Target',
            data: days.map((d) => d.target_kcal),
            borderColor: text,
            borderDash: [6, 4],
            borderWidth: 1.5,
            pointRadius: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: text }, grid: { display: false } },
          y: { beginAtZero: true, ticks: { color: text }, grid: { color: grid } },
        },
      },
    });
  }
}

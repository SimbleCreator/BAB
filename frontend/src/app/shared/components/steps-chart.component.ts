import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  afterRenderEffect,
  input,
  OnDestroy,
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

import { DayPoint } from '../../core/api/models';
import { shortDay, weekday } from '../format/dates';

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

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Daily steps as bars with the step goal as a dashed line. */
@Component({
  selector: 'app-steps-chart',
  template: '<div class="wrap"><canvas #canvas aria-label="Steps per day"></canvas></div>',
  styles: `
    .wrap {
      position: relative;
      height: 220px;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StepsChartComponent implements OnDestroy {
  readonly days = input.required<DayPoint[]>();
  readonly goal = input.required<number>();

  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private chart: Chart | null = null;

  constructor() {
    afterRenderEffect(() => this.draw(this.days(), this.goal()));
  }

  ngOnDestroy(): void {
    this.chart?.destroy();
  }

  private draw(days: DayPoint[], goal: number): void {
    const primary = cssVar('--mat-sys-primary') || '#ffb59d';
    const muted = 'rgba(124, 58, 237, 0.18)';
    const text = cssVar('--mat-sys-on-surface-variant') || '#d8c2bb';
    const grid = cssVar('--mat-sys-outline-variant') || '#53433f';
    const labels = days.map((d) => (days.length <= 7 ? weekday(d.day) : shortDay(d.day)));

    this.chart?.destroy();
    this.chart = new Chart(this.canvas().nativeElement, {
      data: {
        labels,
        datasets: [
          {
            type: 'bar',
            label: 'Steps',
            data: days.map((d) => d.steps),
            backgroundColor: days.map((d) => (d.goal_met ? primary : muted)),
            borderRadius: 4,
            maxBarThickness: 36,
          },
          {
            type: 'line',
            label: 'Goal',
            data: days.map(() => goal),
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
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => shortDay(days[items[0].dataIndex].day),
            },
          },
        },
        scales: {
          x: {
            ticks: { color: text, maxRotation: 0, autoSkip: true, maxTicksLimit: 8 },
            grid: { display: false },
          },
          y: { beginAtZero: true, ticks: { color: text }, grid: { color: grid } },
        },
      },
    });
  }
}

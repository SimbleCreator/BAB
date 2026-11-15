import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

let nextId = 0;

/** A circular progress ring with a gradient stroke and a value in the middle. */
@Component({
  selector: 'app-progress-ring',
  template: `
    <div class="ring" [style.width.px]="size()" [style.height.px]="size()">
      <svg [attr.viewBox]="'0 0 120 120'" aria-hidden="true">
        <defs>
          <linearGradient [attr.id]="gradId" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" [attr.stop-color]="from()" />
            <stop offset="1" [attr.stop-color]="to()" />
          </linearGradient>
        </defs>
        <circle class="track" cx="60" cy="60" r="50" />
        <circle
          class="bar"
          cx="60"
          cy="60"
          r="50"
          [attr.stroke]="'url(#' + gradId + ')'"
          [style.stroke-dasharray]="circumference"
          [style.stroke-dashoffset]="offset()"
        />
      </svg>
      <div class="center">
        <ng-content />
      </div>
    </div>
  `,
  styles: `
    :host {
      display: inline-block;
    }
    .ring {
      position: relative;
    }
    svg {
      width: 100%;
      height: 100%;
      transform: rotate(-90deg);
      filter: drop-shadow(0 0 10px rgba(255, 106, 61, 0.15));
    }
    circle {
      fill: none;
      stroke-width: 11;
    }
    .track {
      stroke: var(--bab-track, rgba(40, 24, 80, 0.08));
    }
    .bar {
      stroke-linecap: round;
      transition: stroke-dashoffset 1s cubic-bezier(0.22, 1, 0.36, 1);
    }
    .center {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProgressRingComponent {
  readonly value = input.required<number>();
  readonly max = input.required<number>();
  readonly from = input('#ff6a3d');
  readonly to = input('#ffb547');
  readonly size = input(120);

  protected readonly gradId = `bab-ring-${nextId++}`;
  protected readonly circumference = 2 * Math.PI * 50;
  protected readonly offset = computed(() => {
    const max = this.max();
    const pct = max > 0 ? Math.min(1, Math.max(0, this.value() / max)) : 0;
    return this.circumference * (1 - pct);
  });
}

import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/**
 * The B.A.B loader: a jogger running toward a milestone flag.
 * Original artwork drawn in SVG. Use instead of a spinner wherever something is loading.
 */
@Component({
  selector: 'app-loader',
  template: `
    <div class="loader" [class.compact]="compact()" role="status" [attr.aria-label]="label()">
      <svg viewBox="0 0 240 110" aria-hidden="true">
        <defs>
          <linearGradient id="bab-run-flag" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stop-color="#ff4d8d" />
            <stop offset="1" stop-color="#8b5cf6" />
          </linearGradient>
          <linearGradient
            id="bab-run-track"
            gradientUnits="userSpaceOnUse"
            x1="8"
            y1="0"
            x2="232"
            y2="0"
          >
            <stop offset="0" stop-color="#ff6a3d" stop-opacity="0" />
            <stop offset="0.3" stop-color="#ff6a3d" stop-opacity="0.9" />
            <stop offset="1" stop-color="#8b5cf6" stop-opacity="0.9" />
          </linearGradient>
        </defs>

        <!-- Track with moving lane marks -->
        <line
          x1="8"
          y1="96"
          x2="232"
          y2="96"
          stroke="url(#bab-run-track)"
          stroke-width="3"
          stroke-linecap="round"
        />
        <line
          class="lane"
          x1="8"
          y1="104"
          x2="232"
          y2="104"
          stroke="rgba(40,24,80,0.18)"
          stroke-width="2"
          stroke-dasharray="10 12"
          stroke-linecap="round"
        />

        <!-- Milestone flag -->
        <g class="flag">
          <line
            x1="206"
            y1="96"
            x2="206"
            y2="34"
            stroke="#1d1534"
            stroke-width="3"
            stroke-linecap="round"
          />
          <path
            class="cloth"
            d="M207 36 C 218 32, 226 42, 236 37 L 236 55 C 226 60, 218 50, 207 54 Z"
            fill="url(#bab-run-flag)"
          />
          <circle cx="206" cy="33" r="3.5" fill="#ffb547" />
          <circle
            class="pulse"
            cx="206"
            cy="96"
            r="6"
            fill="none"
            stroke="#ff4d8d"
            stroke-width="2"
          />
        </g>

        <!-- Jogger -->
        <g class="runner">
          <g class="bob">
            <!-- back leg -->
            <g class="leg back"><path d="M0 0 L -6 18 L 2 31" /></g>
            <!-- back arm -->
            <g class="arm back"><path d="M2 -24 L -9 -13 L -3 -4" /></g>
            <!-- body -->
            <path class="torso" d="M0 0 L 4 -26" />
            <circle class="head" cx="7" cy="-35" r="7" />
            <!-- front leg -->
            <g class="leg front"><path d="M0 0 L 8 16 L 1 31" /></g>
            <!-- front arm -->
            <g class="arm front"><path d="M2 -24 L 13 -15 L 21 -21" /></g>
          </g>
        </g>
      </svg>
      @if (label()) {
        <span class="text">{{ label() }}</span>
      }
    </div>
  `,
  styles: `
    :host {
      display: block;
    }
    .loader {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 28px 12px;
    }
    .loader.compact {
      padding: 8px;
    }
    svg {
      width: min(260px, 70vw);
      height: auto;
      overflow: visible;
    }
    .compact svg {
      width: 140px;
    }
    .text {
      font-family: var(--bab-font-display, sans-serif);
      font-weight: 600;
      letter-spacing: 0.02em;
      color: var(--bab-text-dim, #a7a3b3);
      animation: fade 1.8s ease-in-out infinite;
    }

    /* Runner: moves from the start of the track toward the flag, then starts again. */
    .runner {
      transform: translate(30px, 62px);
      animation: advance 3.2s cubic-bezier(0.45, 0.05, 0.55, 0.95) infinite;
    }
    .bob {
      animation: bob 0.45s ease-in-out infinite;
    }
    .runner path {
      fill: none;
      stroke: #ff8a50;
      stroke-width: 6;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .runner .back path {
      stroke: #d9541f;
      opacity: 0.85;
    }
    .head {
      fill: #ffb547;
    }
    .leg,
    .arm {
      transform-box: view-box;
    }
    .leg.front {
      transform-origin: 0 0;
      animation: swing 0.45s ease-in-out infinite alternate;
    }
    .leg.back {
      transform-origin: 0 0;
      animation: swing 0.45s ease-in-out infinite alternate-reverse;
    }
    .arm.front {
      transform-origin: 2px -24px;
      animation: swing-arm 0.45s ease-in-out infinite alternate-reverse;
    }
    .arm.back {
      transform-origin: 2px -24px;
      animation: swing-arm 0.45s ease-in-out infinite alternate;
    }
    .lane {
      animation: lane 0.6s linear infinite;
    }
    .cloth {
      transform-origin: 207px 45px;
      animation: wave 1.2s ease-in-out infinite;
    }
    .pulse {
      transform-origin: 206px 96px;
      animation: pulse 1.6s ease-out infinite;
    }

    @keyframes advance {
      0% {
        transform: translate(24px, 62px);
        opacity: 0;
      }
      8% {
        opacity: 1;
      }
      80% {
        transform: translate(176px, 62px);
        opacity: 1;
      }
      100% {
        transform: translate(190px, 62px);
        opacity: 0;
      }
    }
    @keyframes bob {
      0%,
      100% {
        transform: translateY(0);
      }
      50% {
        transform: translateY(-3px);
      }
    }
    @keyframes swing {
      from {
        transform: rotate(-32deg);
      }
      to {
        transform: rotate(32deg);
      }
    }
    @keyframes swing-arm {
      from {
        transform: rotate(-38deg);
      }
      to {
        transform: rotate(30deg);
      }
    }
    @keyframes lane {
      to {
        stroke-dashoffset: -22;
      }
    }
    @keyframes wave {
      0%,
      100% {
        transform: skewY(0deg) scaleX(1);
      }
      50% {
        transform: skewY(-6deg) scaleX(0.94);
      }
    }
    @keyframes pulse {
      0% {
        transform: scale(0.6);
        opacity: 0.9;
      }
      100% {
        transform: scale(2.4);
        opacity: 0;
      }
    }
    @keyframes fade {
      0%,
      100% {
        opacity: 0.55;
      }
      50% {
        opacity: 1;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .runner {
        animation: none;
        transform: translate(120px, 62px);
      }
      .bob,
      .leg,
      .arm,
      .lane,
      .cloth,
      .pulse,
      .text {
        animation: none !important;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoaderComponent {
  readonly label = input('Getting there...');
  readonly compact = input(false);
}

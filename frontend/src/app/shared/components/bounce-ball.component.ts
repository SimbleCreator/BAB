import { ChangeDetectionStrategy, Component, input } from '@angular/core';

let nextId = 0;

/**
 * Bounce, drawn in SVG. A plain orange ball that can turn into its strong form (face,
 * sweatband, flexing arms) and back, and can hold a letter for notifications.
 * Size it with CSS width on the host.
 */
@Component({
  selector: 'app-bounce-ball',
  template: `
    <svg
      viewBox="0 0 120 112"
      [class.buff]="buff()"
      [class.letter]="letter()"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <radialGradient [attr.id]="id + 'b'" cx="0.36" cy="0.32" r="0.75">
          <stop offset="0" stop-color="#ffc061" />
          <stop offset="0.55" stop-color="#ff7a1f" />
          <stop offset="1" stop-color="#e2470a" />
        </radialGradient>
        <linearGradient [attr.id]="id + 'a'" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#ff9a3c" />
          <stop offset="1" stop-color="#e5530f" />
        </linearGradient>
        <clipPath [attr.id]="id + 'c'">
          <circle cx="60" cy="64" r="31" />
        </clipPath>
      </defs>

      <!-- Arms (only in strong form) -->
      <g class="arm left">
        <path class="outline" d="M36 68 L17 63 L13 40" />
        <path class="limb" d="M36 68 L17 63 L13 40" [attr.stroke]="'url(#' + id + 'a)'" />
        <ellipse class="bicep" cx="24" cy="58" rx="10" ry="8.5" [attr.fill]="'url(#' + id + 'a)'" />
        <path class="vein" d="M19 56 Q24 52 30 56" />
        <ellipse
          cx="14"
          cy="49"
          rx="6.5"
          ry="8"
          [attr.fill]="'url(#' + id + 'a)'"
          stroke="#c2410c"
          stroke-width="2"
        />
        <circle cx="13" cy="34" r="9" fill="#ff8a2a" stroke="#c2410c" stroke-width="2.4" />
        <path class="vein" d="M9 31 L17 31 M9 35 L17 35" />
      </g>
      <g class="arm right">
        <path class="outline" d="M84 68 L103 63 L107 40" />
        <path class="limb" d="M84 68 L103 63 L107 40" [attr.stroke]="'url(#' + id + 'a)'" />
        <ellipse class="bicep" cx="96" cy="58" rx="10" ry="8.5" [attr.fill]="'url(#' + id + 'a)'" />
        <path class="vein" d="M101 56 Q96 52 90 56" />
        <ellipse
          cx="106"
          cy="49"
          rx="6.5"
          ry="8"
          [attr.fill]="'url(#' + id + 'a)'"
          stroke="#c2410c"
          stroke-width="2"
        />
        <circle cx="107" cy="34" r="9" fill="#ff8a2a" stroke="#c2410c" stroke-width="2.4" />
        <path class="vein" d="M111 31 L103 31 M111 35 L103 35" />
      </g>

      <!-- Letter held in the right hand -->
      <g class="envelope">
        <rect
          x="94"
          y="6"
          width="26"
          height="19"
          rx="3"
          fill="#fff"
          stroke="#7c3aed"
          stroke-width="2"
        />
        <path d="M95 8 L107 17 L119 8" fill="none" stroke="#7c3aed" stroke-width="2" />
        <circle cx="117" cy="7" r="4.5" fill="#ff2e7e" />
      </g>

      <!-- Body -->
      <g class="body">
        <circle cx="60" cy="64" r="31" [attr.fill]="'url(#' + id + 'b)'" />
        <g [attr.clip-path]="'url(#' + id + 'c)'">
          <path class="seam" d="M29 58 Q60 74 91 58" />
          <path class="seam" d="M60 33 Q48 64 60 95" />
          <rect class="band" x="26" y="40" width="68" height="8" fill="#ff2e7e" />
          <path
            class="abs"
            d="M40 76 Q50 81 60 76 Q70 81 80 76 M54 86 Q60 88 66 86 M60 78 L60 90"
          />
        </g>
        <ellipse
          cx="48"
          cy="49"
          rx="8"
          ry="5"
          fill="#fff"
          opacity="0.45"
          transform="rotate(-25 48 49)"
        />
      </g>

      <!-- Face (only in strong form) -->
      <g class="face">
        <path
          d="M43 52 L55 56 M77 52 L65 56"
          stroke="#3b1408"
          stroke-width="3.2"
          stroke-linecap="round"
        />
        <ellipse cx="51" cy="62" rx="4.6" ry="5.4" fill="#fff" />
        <ellipse cx="69" cy="62" rx="4.6" ry="5.4" fill="#fff" />
        <circle cx="52" cy="63" r="2.5" fill="#1d1534" />
        <circle cx="68" cy="63" r="2.5" fill="#1d1534" />
        <path
          d="M49 72 Q60 82 71 72 Z"
          fill="#fff"
          stroke="#3b1408"
          stroke-width="2.4"
          stroke-linejoin="round"
        />
      </g>
    </svg>
  `,
  styles: `
    :host {
      display: inline-block;
      width: 48px;
      line-height: 0;
    }
    svg {
      width: 100%;
      height: auto;
      overflow: visible;
    }
    .arm path {
      fill: none;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .arm .outline {
      stroke: #c2410c;
      stroke-width: 17;
    }
    .arm .limb {
      stroke-width: 13;
    }
    .arm .vein {
      stroke: rgba(122, 31, 0, 0.45);
      stroke-width: 1.8;
    }
    .bicep {
      stroke: #c2410c;
      stroke-width: 2;
    }
    .arm,
    .face,
    .envelope,
    .band,
    .abs,
    .body {
      transform-box: view-box;
      transition:
        transform 0.32s cubic-bezier(0.34, 1.56, 0.64, 1),
        opacity 0.2s ease;
    }
    .arm {
      transform: scale(0);
      opacity: 0;
    }
    .arm.left {
      transform-origin: 36px 68px;
    }
    .arm.right {
      transform-origin: 84px 68px;
    }
    .face {
      opacity: 0;
      transform: scale(0.6);
      transform-origin: 60px 64px;
    }
    .body {
      transform-origin: 60px 95px;
    }
    .seam {
      fill: none;
      stroke: rgba(122, 31, 0, 0.28);
      stroke-width: 2;
      transition: opacity 0.2s ease;
    }
    .band,
    .abs {
      opacity: 0;
    }
    .abs {
      fill: none;
      stroke: rgba(122, 31, 0, 0.45);
      stroke-width: 2;
      stroke-linecap: round;
    }
    .envelope {
      opacity: 0;
      transform: scale(0.3);
      transform-origin: 107px 34px;
    }

    /* Strong form */
    .buff .arm,
    .letter .arm {
      transform: scale(1);
      opacity: 1;
    }
    .buff .face,
    .letter .face {
      opacity: 1;
      transform: scale(1);
    }
    .buff .band,
    .buff .abs,
    .letter .band,
    .letter .abs {
      opacity: 1;
    }
    .buff .seam,
    .letter .seam {
      opacity: 0;
    }
    .buff .body {
      transform: scale(1.07, 1.03);
    }
    .buff .bicep {
      animation: flex 0.6s ease-in-out 0.2s 2;
    }
    .letter .envelope {
      opacity: 1;
      transform: scale(1);
    }
    @keyframes flex {
      50% {
        transform: scale(1.35);
      }
    }
    .bicep {
      transform-box: fill-box;
      transform-origin: center;
    }
    @media (prefers-reduced-motion: reduce) {
      .buff .bicep {
        animation: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BounceBallComponent {
  /** The strong form: face, sweatband and flexing arms. */
  readonly buff = input(false);
  /** Strong form holding a letter (a notification). */
  readonly letter = input(false);

  protected readonly id = `bb${nextId++}-`;
}

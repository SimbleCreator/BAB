import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  Injector,
  OnDestroy,
  afterNextRender,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { RouterLink } from '@angular/router';

import { BounceApi } from '../api/bounce.api';
import { BounceNotificationOut } from '../api/models';
import { BounceBallComponent } from '../../shared/components/bounce-ball.component';

const FLYER = 56; // px, size of the flying ball
const KEY_BALL = 34; // px, size of the ball sitting in the dock key
const SEEN_KEY = 'bab.bounce.seen';

const ROUTE: Record<BounceNotificationOut['kind'], string> = {
  checkin: '/checkin',
  meals: '/eat',
  activity: '/activity',
};

interface Point {
  x: number;
  y: number;
}

function reducedMotion(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
}

function rand(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function readSeen(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(SEEN_KEY) ?? '[]');
    return Array.isArray(v) ? v.filter((x) => typeof x === 'string') : [];
  } catch {
    return [];
  }
}

function writeSeen(ids: string[]): void {
  try {
    localStorage.setItem(SEEN_KEY, JSON.stringify(ids.slice(-30)));
  } catch {
    // Private mode or blocked storage: the note simply shows again next time.
  }
}

/**
 * Bounce the mascot, drawn over the app: bounces in from the left and lands in the dock
 * key when you come back to Home, and jumps out with a letter when there is a notification.
 */
@Component({
  selector: 'app-bounce-mascot',
  imports: [BounceBallComponent, RouterLink],
  template: `
    <div class="flyer" #flyer [class.on]="flyerOn()" aria-hidden="true">
      <app-bounce-ball [buff]="flyBuff()" />
    </div>

    @if (noteOpen() && note(); as n) {
      <div class="messenger" #messenger>
        <div class="bubble" role="status" aria-live="polite">
          <span class="who">Bounce</span>
          <strong>{{ n.title }}</strong>
          <p>{{ n.message }}</p>
          <div class="actions">
            <a class="go" [routerLink]="route(n)" (click)="dismiss(n, true)">{{
              n.action_label
            }}</a>
            <button class="later" type="button" (click)="dismiss(n, false)">Later</button>
          </div>
        </div>
        <div class="holder" #holder>
          <app-bounce-ball [letter]="true" />
        </div>
      </div>
    }
  `,
  styles: `
    .flyer {
      position: fixed;
      top: 0;
      left: 0;
      z-index: 8;
      width: ${FLYER}px;
      pointer-events: none;
      visibility: hidden;
      will-change: transform;
      filter: drop-shadow(0 10px 10px rgba(122, 31, 0, 0.25));

      &.on {
        visibility: visible;
      }

      app-bounce-ball {
        width: 100%;
      }
    }

    .messenger {
      position: fixed;
      right: 10px;
      bottom: calc(176px + env(safe-area-inset-bottom));
      z-index: 8;
      display: flex;
      align-items: flex-end;
      gap: 6px;
      max-width: calc(100vw - 20px);
    }

    .holder {
      flex: none;
      width: 74px;
      filter: drop-shadow(0 10px 12px rgba(122, 31, 0, 0.28));

      app-bounce-ball {
        width: 100%;
      }
    }

    .bubble {
      position: relative;
      width: min(260px, calc(100vw - 110px));
      margin-bottom: 40px;
      padding: 12px 14px 10px;
      border-radius: 20px 20px 6px 20px;
      background: #fff;
      border: 1px solid rgba(124, 58, 237, 0.18);
      box-shadow: 0 18px 40px rgba(40, 24, 80, 0.22);
      animation: pop 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) 0.75s both;

      .who {
        display: block;
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--bab-violet);
      }

      strong {
        font-family: var(--bab-font-display);
        font-size: 1.02rem;
      }

      p {
        margin: 4px 0 8px;
        font-size: 0.9rem;
        line-height: 1.35;
        color: var(--bab-text);
      }
    }

    .actions {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;

      a,
      button {
        display: inline-flex;
        align-items: center;
        height: 36px;
        padding: 0 16px;
        border-radius: 999px;
        font: inherit;
        font-size: 0.88rem;
        font-weight: 700;
        text-decoration: none;
        cursor: pointer;
      }

      .go {
        color: #fff;
        background: var(--bab-grad-primary);
        box-shadow: var(--bab-glow-orange);
      }

      .later {
        border: 0;
        background: transparent;
        color: var(--bab-text-dim);
      }
    }

    @keyframes pop {
      from {
        opacity: 0;
        transform: translateX(16px) scale(0.85);
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .bubble {
        animation: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BounceMascotComponent implements OnDestroy {
  private readonly api = inject(BounceApi);
  private readonly injector = inject(Injector);

  /** The dock key Bounce lands in and jumps out of. */
  readonly anchor = input<HTMLElement | undefined>();

  private readonly flyerEl = viewChild<ElementRef<HTMLElement>>('flyer');
  private readonly holderEl = viewChild<ElementRef<HTMLElement>>('holder');

  protected readonly flyerOn = signal(false);
  protected readonly flyBuff = signal(false);
  /** True while the ball is away from the key (flying or out with a letter). */
  readonly away = signal(false);
  /** The key ball's strong form. */
  readonly keyBuff = signal(false);
  /** A notification the user has not dismissed yet. */
  readonly note = signal<BounceNotificationOut | null>(null);
  readonly noteOpen = signal(false);

  private timers: ReturnType<typeof setTimeout>[] = [];
  private flight: Animation | null = null;
  private readonly idle = setInterval(() => {
    if (!this.away() && !reducedMotion() && document.visibilityState === 'visible') this.flex();
  }, 7000);

  ngOnDestroy(): void {
    clearInterval(this.idle);
    this.clearTimers();
    this.flight?.cancel();
  }

  /** Fetch the current notification (also used for the badge on the key). */
  refresh(then?: () => void): void {
    this.api.status().subscribe({
      next: (s) => {
        const n = s.notification;
        this.note.set(n && !readSeen().includes(n.id) ? n : null);
        then?.();
      },
      error: () => then?.(),
    });
  }

  /** Coming back to Home: bounce in from the left, land in the key, then any letter. */
  arrive(): void {
    if (this.away()) return;
    let landed = false;
    let fetched = false;
    const next = () => {
      if (landed && fetched && this.note()) this.jumpOut();
    };
    this.refresh(() => {
      fetched = true;
      next();
    });
    this.fly().then(() => {
      landed = true;
      next();
    });
  }

  /** The ball in the key turns strong for a moment and back. */
  flex(ms = 1300): void {
    this.keyBuff.set(true);
    this.later(() => this.keyBuff.set(false), ms);
  }

  protected route(n: BounceNotificationOut): string {
    return ROUTE[n.kind];
  }

  /** Hide the note for today (it comes back if the API sends a different one). */
  protected dismiss(n: BounceNotificationOut, acted: boolean): void {
    writeSeen([...readSeen().filter((id) => id !== n.id), n.id]);
    const finish = () => {
      this.noteOpen.set(false);
      this.note.set(null);
      this.away.set(false);
      if (!acted) this.flex(900);
    };
    const holder = this.holderEl()?.nativeElement;
    const key = this.keyCenter();
    if (acted || !holder || !key || reducedMotion()) {
      finish();
      return;
    }
    const r = holder.getBoundingClientRect();
    const dx = key.x - (r.left + r.width / 2);
    const dy = key.y - (r.top + r.height / 2);
    const back = holder.animate(this.arc({ x: 0, y: 0 }, { x: dx, y: dy }, 140, 0.4), {
      duration: 520,
      fill: 'forwards',
    });
    back.finished.then(finish, finish);
  }

  // Animation helpers ------------------------------------------------------------------

  private keyCenter(): Point | null {
    const a = this.anchor();
    if (!a) return null;
    const r = a.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height * 0.42 };
  }

  /** Keyframes along a parabola from a to b, peaking `height` px above the higher end. */
  private arc(a: Point, b: Point, height: number, endScale = 1): Keyframe[] {
    const frames: Keyframe[] = [];
    const steps = 14;
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const x = a.x + (b.x - a.x) * t;
      const y = a.y + (b.y - a.y) * t - 4 * height * t * (1 - t);
      const s = 1 + (endScale - 1) * t;
      frames.push({ transform: `translate(${x}px, ${y}px) scale(${s})`, offset: t });
    }
    return frames;
  }

  /** 2 or 3 random pitches across the screen from the left, ending in the key. */
  private fly(): Promise<void> {
    const el = this.flyerEl()?.nativeElement;
    const key = this.keyCenter();
    if (!el || !key || reducedMotion()) {
      this.flex();
      return Promise.resolve();
    }
    const W = window.innerWidth;
    const H = window.innerHeight;
    const half = FLYER / 2;
    const pitches = Math.random() < 0.5 ? 2 : 3;

    const pts: Point[] = [{ x: -FLYER - 10, y: H * rand(0.18, 0.4) }];
    for (let i = 1; i <= pitches; i++) {
      pts.push({
        x: W * (0.1 + (0.8 * i) / (pitches + 1)) + rand(-0.06, 0.06) * W - half,
        y: H * rand(0.48, 0.66),
      });
    }
    pts.push({ x: key.x - half, y: key.y - half });

    // Build one timeline: arcs with a short squash at each landing.
    const segMs = pts.slice(1).map((_, i) => (i === pitches ? 620 : rand(430, 560)));
    const contact = 70;
    const total = segMs.reduce((a, b) => a + b, 0) + contact * pitches;
    const frames: Keyframe[] = [];
    let at = 0;
    const landingTimes: number[] = [];
    for (let s = 0; s < pts.length - 1; s++) {
      const a = pts[s];
      const b = pts[s + 1];
      const last = s === pts.length - 2;
      const height = last ? rand(90, 150) : rand(140, Math.max(160, H * 0.32));
      const endScale = last ? KEY_BALL / FLYER : 1;
      for (const f of this.arc(a, b, height, endScale)) {
        frames.push({ ...f, offset: (at + segMs[s] * (f.offset as number)) / total });
      }
      at += segMs[s];
      if (!last) {
        landingTimes.push(at);
        // Squash on the ground, then spring up.
        frames.push({
          transform: `translate(${b.x}px, ${b.y + FLYER * 0.12}px) scale(1.25, 0.75)`,
          offset: (at + contact * 0.5) / total,
        });
        at += contact;
        frames.push({
          transform: `translate(${b.x}px, ${b.y}px) scale(0.92, 1.1)`,
          offset: at / total,
        });
      }
    }

    this.clearTimers();
    this.flight?.cancel();
    this.away.set(true);
    this.flyerOn.set(true);
    // Turn strong around a middle landing, then back to a ball before the key.
    const mid = landingTimes[Math.floor((landingTimes.length - 1) / 2)];
    this.later(() => this.flyBuff.set(true), Math.max(0, mid - 120));
    this.later(() => this.flyBuff.set(false), mid + 620);

    const anim = el.animate(frames, { duration: total, easing: 'linear', fill: 'forwards' });
    this.flight = anim;
    const done = () => {
      this.flyerOn.set(false);
      this.flyBuff.set(false);
      this.away.set(false);
      this.flex();
    };
    return anim.finished.then(done, done);
  }

  /** Jump from the key to the right side, holding the letter. */
  private jumpOut(): void {
    this.away.set(true);
    this.noteOpen.set(true);
    afterNextRender(
      () => {
        const holder = this.holderEl()?.nativeElement;
        const key = this.keyCenter();
        if (!holder || !key || reducedMotion()) return;
        const r = holder.getBoundingClientRect();
        const from = { x: key.x - (r.left + r.width / 2), y: key.y - (r.top + r.height / 2) };
        holder.animate(this.arc(from, { x: 0, y: 0 }, 160), {
          duration: 640,
          easing: 'linear',
          fill: 'backwards',
        });
      },
      { injector: this.injector },
    );
  }

  private later(fn: () => void, ms: number): void {
    this.timers.push(setTimeout(fn, ms));
  }

  private clearTimers(): void {
    this.timers.forEach(clearTimeout);
    this.timers = [];
  }
}

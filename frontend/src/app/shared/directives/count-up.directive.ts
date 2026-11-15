import { Directive, ElementRef, OnDestroy, effect, inject, input } from '@angular/core';

const FMT = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

/** Counts a number up from its previous value. Shows the final value at once when the
 * user prefers reduced motion. Usage: <span [appCountUp]="9500"></span> */
@Directive({ selector: '[appCountUp]' })
export class CountUpDirective implements OnDestroy {
  readonly appCountUp = input.required<number>();
  readonly suffix = input('');

  private readonly el = inject(ElementRef<HTMLElement>);
  private frame = 0;
  private shown = 0;

  constructor() {
    effect(() => this.run(this.appCountUp() ?? 0, this.suffix()));
  }

  ngOnDestroy(): void {
    cancelAnimationFrame(this.frame);
  }

  private run(target: number, suffix: string): void {
    cancelAnimationFrame(this.frame);
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    // Hidden tabs do not run animation frames: show the value straight away.
    if (reduce || document.hidden || typeof requestAnimationFrame === 'undefined') {
      this.write(target, suffix);
      return;
    }
    const from = this.shown;
    const start = performance.now();
    const duration = 900;
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      this.write(from + (target - from) * eased, suffix);
      if (t < 1) this.frame = requestAnimationFrame(step);
    };
    this.frame = requestAnimationFrame(step);
  }

  private write(value: number, suffix: string): void {
    this.shown = value;
    this.el.nativeElement.textContent = FMT.format(Math.round(value)) + suffix;
  }
}

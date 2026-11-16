import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  signal,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormControl } from '@angular/forms';
import { of } from 'rxjs';

import { NutritionApi } from '../../core/api/nutrition.api';
import { LoaderComponent } from '../components/loader.component';
import { USUAL_FOODS_MAX } from './profile-form';

/**
 * Pick the dishes eaten at home most days. Lists dishes for the diet type, the user's
 * region first, and writes the chosen food codes into the given form control.
 */
@Component({
  selector: 'app-usual-foods-picker',
  imports: [LoaderComponent],
  template: `
    <p class="lead">
      Pick up to {{ max }} dishes you eat at home most days. Bounce builds your meal plan around
      them instead of swapping them for food you do not eat.
    </p>

    @if (!dietType()) {
      <p class="bab-muted">Choose your diet first.</p>
    } @else if (staples.isLoading() && !staples.hasValue()) {
      <div class="loading"><app-loader [compact]="true" label="" /></div>
    } @else if (staples.error()) {
      <p class="bab-form-error" role="alert">Could not load dishes.</p>
      <button type="button" class="text-btn" (click)="staples.reload()">Try again</button>
    } @else {
      @if (chosen().length) {
        <div class="chosen" aria-label="Your usual dishes">
          @for (c of chosen(); track c.food_code) {
            <button type="button" class="chip on" (click)="toggle(c.food_code)">
              {{ c.name }} <span aria-hidden="true">✕</span>
              <span class="sr-only">Remove</span>
            </button>
          }
        </div>
      }
      <p class="count" aria-live="polite">{{ selected().length }} of {{ max }} picked</p>

      <label class="search">
        <span class="sr-only">Search dishes</span>
        <input
          type="search"
          placeholder="Search dishes, e.g. dal, dosa, roti"
          [value]="query()"
          (input)="query.set($any($event.target).value)"
        />
      </label>

      <div class="options">
        @for (s of visible(); track s.food_code) {
          <button
            type="button"
            class="chip"
            [class.on]="isOn(s.food_code)"
            [attr.aria-pressed]="isOn(s.food_code)"
            [disabled]="!isOn(s.food_code) && full()"
            (click)="toggle(s.food_code)"
          >
            {{ s.name }}
            @if (s.regional) {
              <span class="local">local</span>
            }
          </button>
        } @empty {
          <p class="bab-muted">No dishes match.</p>
        }
      </div>
      @if (hidden() > 0) {
        <p class="bab-muted small">
          {{ hidden() }} more. Search to find them. Missing a dish? Add it later as your own food on
          the Eat page.
        </p>
      }
    }
  `,
  styles: `
    :host {
      display: block;
    }
    .lead {
      margin: 0 0 8px;
      font: var(--mat-sys-body-medium);
    }
    .loading {
      display: grid;
      place-items: center;
      padding: 12px;
    }
    .chosen,
    .options {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .count {
      margin: 8px 0;
      font: var(--mat-sys-label-medium);
      color: var(--mat-sys-on-surface-variant);
    }
    .search input {
      width: 100%;
      box-sizing: border-box;
      padding: 10px 14px;
      margin-bottom: 10px;
      border: 1px solid var(--mat-sys-outline-variant);
      border-radius: 999px;
      background: var(--mat-sys-surface);
      color: var(--mat-sys-on-surface);
      font: var(--mat-sys-body-medium);
    }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 36px;
      padding: 6px 12px;
      border: 1px solid var(--mat-sys-outline-variant);
      border-radius: 999px;
      background: var(--mat-sys-surface);
      color: var(--mat-sys-on-surface);
      font: var(--mat-sys-label-large);
      cursor: pointer;
    }
    .chip.on {
      border-color: transparent;
      background: linear-gradient(135deg, #10b981, #14b8a6);
      color: #fff;
    }
    .chip:disabled {
      opacity: 0.45;
      cursor: default;
    }
    .local {
      padding: 1px 6px;
      border-radius: 999px;
      background: rgba(16, 185, 129, 0.15);
      color: #047857;
      font-size: 11px;
    }
    .chip.on .local {
      background: rgba(255, 255, 255, 0.25);
      color: #fff;
    }
    .small {
      font: var(--mat-sys-body-small);
    }
    .text-btn {
      border: 0;
      background: none;
      color: var(--mat-sys-primary);
      font: var(--mat-sys-label-large);
      cursor: pointer;
    }
    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UsualFoodsPickerComponent {
  private readonly api = inject(NutritionApi);

  readonly control = input.required<FormControl<string[]>>();
  readonly dietType = input<string | null>(null);
  readonly state = input<string | null>(null);

  protected readonly max = USUAL_FOODS_MAX;
  /** Dishes shown before searching. */
  private readonly shownMax = 40;

  protected readonly query = signal('');
  protected readonly selected = signal<string[]>([]);

  protected readonly staples = rxResource({
    params: () => ({ diet: this.dietType(), state: this.state() }),
    stream: ({ params }) => (params.diet ? this.api.staples(params.diet, params.state) : of([])),
  });

  private readonly byCode = computed(
    () => new Map((this.staples.value() ?? []).map((s) => [s.food_code, s])),
  );
  protected readonly chosen = computed(() =>
    this.selected()
      .map((c) => this.byCode().get(c))
      .filter((s) => s !== undefined),
  );
  private readonly matches = computed(() => {
    const q = this.query().trim().toLowerCase();
    const all = this.staples.value() ?? [];
    return q ? all.filter((s) => s.name.toLowerCase().includes(q)) : all;
  });
  protected readonly visible = computed(() => this.matches().slice(0, this.shownMax));
  protected readonly hidden = computed(() => this.matches().length - this.visible().length);
  protected readonly full = computed(() => this.selected().length >= this.max);

  constructor() {
    // Mirror the form control (it can be patched from the server after load).
    effect((onCleanup) => {
      const c = this.control();
      this.selected.set(c.value ?? []);
      const sub = c.valueChanges.subscribe((v) => this.selected.set(v ?? []));
      onCleanup(() => sub.unsubscribe());
    });
    // A diet change can rule out picked dishes (an egg dish after switching to veg).
    effect(() => {
      const known = this.byCode();
      if (!this.staples.hasValue() || this.staples.isLoading()) return;
      const kept = this.selected().filter((c) => known.has(c));
      if (kept.length !== this.selected().length) this.write(kept);
    });
  }

  protected isOn(code: string): boolean {
    return this.selected().includes(code);
  }

  protected toggle(code: string): void {
    const cur = this.selected();
    if (cur.includes(code)) this.write(cur.filter((c) => c !== code));
    else if (cur.length < this.max) this.write([...cur, code]);
  }

  private write(codes: string[]): void {
    const c = this.control();
    c.setValue(codes);
    c.markAsDirty();
  }
}

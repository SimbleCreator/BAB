import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { apiErrorMessage } from '../../core/api/api-error';
import { BounceApi } from '../../core/api/bounce.api';
import { SnapshotOut } from '../../core/api/models';
import { parseDay } from '../../shared/format/dates';

const DATE = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'long', year: 'numeric' });
const INT = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

interface Row {
  label: string;
  then: string;
  now: string;
}

/** "A letter from you, 90 days from now": write, wait (sealed), open beside real progress. */
@Component({
  selector: 'app-letter-card',
  imports: [MatButtonModule, MatIconModule],
  template: `
    @if (data.value(); as d) {
      @if (d.enabled || d.state !== 'none') {
        <div class="letter-card bab-panel" [class.ready]="d.state === 'ready'">
          <h2><mat-icon>mail</mat-icon>A letter from future you</h2>

          @switch (d.state) {
            @case ('none') {
              <p>
                Bounce writes a letter from you, 90 days from now, using your real plan, food and
                routine. It stays sealed until then, and opens next to your actual progress.
              </p>
              <button mat-flat-button type="button" (click)="write()" [disabled]="busy()">
                {{ busy() ? 'Writing your letter...' : 'Write my letter' }}
              </button>
            }
            @case ('sealed') {
              <div class="sealed">
                <span class="seal" aria-hidden="true"><mat-icon>lock</mat-icon></span>
                <div>
                  <p class="count">{{ d.days_left }} days to go</p>
                  <p class="bab-muted">
                    Sealed on {{ day(d.written_on) }}. Opens on {{ day(d.open_on) }}. Keep going
                    until then.
                  </p>
                </div>
              </div>
            }
            @case ('ready') {
              <p class="count">Your letter is ready.</p>
              <p class="bab-muted">You wrote it on {{ day(d.written_on) }}. Open it now?</p>
              <button mat-flat-button type="button" (click)="open()" [disabled]="busy()">
                Open my letter
              </button>
            }
            @case ('opened') {
              @if (d.letter; as l) {
                <article class="paper">
                  <p class="greet">{{ l.greeting }}</p>
                  @for (p of l.paragraphs; track $index) {
                    <p>{{ p }}</p>
                  }
                  <p class="sign">{{ l.sign_off }}</p>
                  <p class="bab-muted small">Written {{ day(l.written_on) }}</p>
                </article>
              }
              @if (rows().length) {
                <h3>Then and now</h3>
                <table>
                  <thead>
                    <tr>
                      <th scope="col"></th>
                      <th scope="col">{{ day(d.written_on) }}</th>
                      <th scope="col">Today</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (r of rows(); track r.label) {
                      <tr>
                        <th scope="row">{{ r.label }}</th>
                        <td>{{ r.then }}</td>
                        <td>{{ r.now }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              }
              @if (d.can_write) {
                <button mat-stroked-button type="button" (click)="write()" [disabled]="busy()">
                  {{ busy() ? 'Writing...' : 'Write a letter for the next 90 days' }}
                </button>
              }
            }
          }
          @if (error()) {
            <p class="bab-form-error" role="alert">{{ error() }}</p>
          }
          <p class="bab-muted small">
            Written by an AI model and checked by B.A.B: it talks about habits, never promises a
            number.
          </p>
        </div>
      }
    }
  `,
  styles: `
    .letter-card {
      margin: 16px 0;
      padding: 18px;
      border-radius: 24px;
    }
    .letter-card.ready {
      outline: 2px solid rgba(255, 46, 126, 0.45);
    }
    h2 {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 8px;
      font: var(--mat-sys-title-large);
    }
    h2 mat-icon {
      color: #ff2e7e;
    }
    h3 {
      margin: 16px 0 6px;
      font: var(--mat-sys-title-medium);
    }
    .sealed {
      display: flex;
      gap: 14px;
      align-items: center;
    }
    .seal {
      display: grid;
      place-items: center;
      flex: none;
      width: 52px;
      height: 52px;
      border-radius: 50%;
      background: var(--bab-grad-hero);
      color: #fff;
      box-shadow: 0 6px 18px rgba(255, 46, 126, 0.35);
    }
    .count {
      margin: 0;
      font: var(--mat-sys-headline-small);
      font-weight: 800;
    }
    .paper {
      padding: 18px 20px;
      border-radius: 18px;
      background: #fffdf7;
      border: 1px solid #f3e6c8;
      font: var(--mat-sys-body-large);
      line-height: 1.6;
    }
    .greet,
    .sign {
      font-weight: 700;
    }
    .sign {
      text-align: right;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 12px;
    }
    th,
    td {
      padding: 6px 4px;
      text-align: right;
      border-bottom: 1px solid var(--mat-sys-outline-variant);
      font: var(--mat-sys-body-medium);
    }
    th[scope='row'],
    thead th:first-child {
      text-align: left;
    }
    .small {
      font: var(--mat-sys-body-small);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LetterCardComponent {
  private readonly api = inject(BounceApi);

  protected readonly data = rxResource({ stream: () => this.api.letter() });
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly rows = computed<Row[]>(() => {
    const d = this.data.value();
    if (!d?.then || !d.now) return [];
    return rowsFor(d.then, d.now);
  });

  protected day(d: string | null): string {
    return d ? DATE.format(parseDay(d)) : '';
  }

  protected write(): void {
    this.run(this.api.writeLetter());
  }

  protected open(): void {
    this.run(this.api.openLetter());
  }

  private run(obs: ReturnType<BounceApi['letter']>): void {
    this.busy.set(true);
    this.error.set(null);
    obs.subscribe({
      next: (d) => {
        this.busy.set(false);
        this.data.set(d);
      },
      error: (err: unknown) => {
        this.busy.set(false);
        this.error.set(apiErrorMessage(err));
      },
    });
  }
}

function rowsFor(then: SnapshotOut, now: SnapshotOut): Row[] {
  const kg = (v: number | null) => (v === null ? '–' : `${v} kg`);
  const rows: Row[] = [{ label: 'Weight', then: kg(then.weight_kg), now: kg(now.weight_kg) }];
  if (then.waist_cm !== null || now.waist_cm !== null) {
    const cm = (v: number | null) => (v === null ? '–' : `${v} cm`);
    rows.push({ label: 'Waist', then: cm(then.waist_cm), now: cm(now.waist_cm) });
  }
  const steps = (v: number | null) => (v === null ? '–' : INT.format(v));
  rows.push(
    { label: 'Steps a day', then: steps(then.avg_steps_7d), now: steps(now.avg_steps_7d) },
    {
      label: 'Workouts (4 weeks)',
      then: String(then.workouts_28d),
      now: String(now.workouts_28d),
    },
    {
      label: 'Days of meals logged (4 weeks)',
      then: String(then.meal_days_28d),
      now: String(now.meal_days_28d),
    },
  );
  return rows;
}

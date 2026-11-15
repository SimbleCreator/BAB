import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { TrainingApi } from '../../core/api/training.api';
import { GROUP_LABEL } from './format';

@Component({
  selector: 'app-exercise-detail-page',
  imports: [RouterLink, MatButtonModule, MatIconModule, MatProgressSpinnerModule],
  template: `
    <section class="bab-page">
      <a mat-button routerLink="/train/exercises" class="back">
        <mat-icon>arrow_back</mat-icon> Exercise library
      </a>
      @if (one.isLoading()) {
        <div class="center"><mat-spinner diameter="36" /></div>
      } @else if (one.error()) {
        <p class="bab-form-error">Exercise not found.</p>
      } @else if (one.value(); as e) {
        <h1 class="bab-page-title">{{ e.name }}</h1>
        <p class="bab-muted">
          {{ label[e.group] }} &middot; difficulty {{ e.difficulty }} of 5 &middot;
          {{ e.type === 'timed' ? 'timed hold' : 'reps' }}
          @if (e.needs_bar) {
            &middot; needs a pull-up bar
          }
        </p>
        <p class="how">{{ e.instructions }}</p>
        <div class="links">
          @if (e.easier; as code) {
            <a mat-stroked-button [routerLink]="['/train/exercises', code]">
              <mat-icon>south</mat-icon> Easier: {{ nameOf(code) }}
            </a>
          }
          @if (e.harder; as code) {
            <a mat-stroked-button [routerLink]="['/train/exercises', code]">
              <mat-icon>north</mat-icon> Harder: {{ nameOf(code) }}
            </a>
          }
        </div>
        <p class="bab-disclaimer">Move within a pain-free range. Not medical advice.</p>
      }
    </section>
  `,
  styles: `
    .back {
      margin-left: -8px;
    }
    .center {
      display: flex;
      justify-content: center;
      padding: 32px;
    }
    .how {
      font: var(--mat-sys-body-large);
      line-height: 1.6;
    }
    .links {
      display: flex;
      flex-direction: column;
      gap: 8px;
      align-items: flex-start;
      margin: 16px 0;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExerciseDetailPage {
  private readonly api = inject(TrainingApi);
  /** Route parameter. */
  readonly code = input.required<string>();
  protected readonly one = rxResource({
    params: () => this.code(),
    stream: ({ params }) => this.api.exercise(params),
  });
  private readonly all = rxResource({ stream: () => this.api.exercises() });
  private readonly names = computed(
    () => new Map((this.all.value() ?? []).map((e) => [e.code, e.name] as const)),
  );
  protected readonly label = GROUP_LABEL;

  protected nameOf(code: string): string {
    return this.names().get(code) ?? code;
  }
}

import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { Group } from '../../core/api/models';
import { TrainingApi } from '../../core/api/training.api';
import { GROUP_LABEL } from './format';

@Component({
  selector: 'app-exercises-page',
  imports: [
    RouterLink,
    MatButtonModule,
    MatButtonToggleModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <section class="bab-page">
      <a mat-button routerLink="/train" class="back"><mat-icon>arrow_back</mat-icon> Plan</a>
      <h1 class="bab-page-title">Exercise library</h1>
      <input
        class="search"
        type="search"
        placeholder="Search exercises"
        aria-label="Search exercises"
        [value]="query()"
        (input)="query.set($any($event.target).value)"
      />
      <div class="filters">
        <mat-button-toggle-group
          [value]="group()"
          (change)="group.set($event.value)"
          aria-label="Muscle group"
          hideSingleSelectionIndicator
        >
          <mat-button-toggle value="all">All</mat-button-toggle>
          @for (g of groups; track g) {
            <mat-button-toggle [value]="g">{{ label[g] }}</mat-button-toggle>
          }
        </mat-button-toggle-group>
      </div>
      @if (list.isLoading()) {
        <div class="center"><mat-spinner diameter="36" /></div>
      } @else if (list.error()) {
        <p class="bab-form-error">Could not load exercises.</p>
        <button mat-button type="button" (click)="list.reload()">Try again</button>
      } @else {
        @if (filtered().length === 0) {
          <p class="bab-muted">No exercises match.</p>
        }
        @for (e of filtered(); track e.code) {
          <a class="row" [routerLink]="['/train/exercises', e.code]">
            <div>
              <div class="name">{{ e.name }}</div>
              <div class="bab-muted meta">
                {{ label[e.group] }} &middot; {{ e.type === 'timed' ? 'hold' : 'reps' }}
                @if (e.needs_bar) {
                  &middot; pull-up bar
                }
              </div>
            </div>
            <span class="level" [attr.aria-label]="'Difficulty ' + e.difficulty + ' of 5'">
              @for (i of [1, 2, 3, 4, 5]; track i) {
                <span class="pip" [class.on]="i <= e.difficulty"></span>
              }
            </span>
          </a>
        }
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
    .search {
      width: 100%;
      box-sizing: border-box;
      padding: 12px 14px;
      border-radius: 12px;
      border: 1px solid var(--mat-sys-outline);
      background: var(--mat-sys-surface-container);
      color: var(--mat-sys-on-surface);
      font: var(--mat-sys-body-large);
      margin-bottom: 12px;
    }
    .filters {
      overflow-x: auto;
      margin-bottom: 12px;
    }
    .row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 12px 4px;
      border-bottom: 1px solid var(--mat-sys-outline-variant);
      color: inherit;
      text-decoration: none;
    }
    .name {
      font: var(--mat-sys-body-large);
    }
    .meta {
      font: var(--mat-sys-body-small);
    }
    .level {
      display: inline-flex;
      gap: 3px;
    }
    .pip {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--mat-sys-outline-variant);
    }
    .pip.on {
      background: var(--mat-sys-primary);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExercisesPage {
  private readonly api = inject(TrainingApi);
  protected readonly list = rxResource({ stream: () => this.api.exercises() });
  protected readonly query = signal('');
  protected readonly group = signal<Group | 'all'>('all');
  protected readonly groups: Group[] = ['push', 'pull', 'legs', 'core', 'cardio'];
  protected readonly label = GROUP_LABEL;

  protected readonly filtered = computed(() => {
    const q = this.query().trim().toLowerCase();
    const g = this.group();
    return (this.list.value() ?? [])
      .filter((e) => (g === 'all' || e.group === g) && (!q || e.name.toLowerCase().includes(q)))
      .sort((a, b) => a.group.localeCompare(b.group) || a.difficulty - b.difficulty);
  });
}

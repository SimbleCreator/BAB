import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatRadioModule } from '@angular/material/radio';

import { HabitForm } from './habit-setup';
import { HABIT } from './wording';

@Component({
  selector: 'app-habit-setup',
  imports: [
    ReactiveFormsModule,
    MatButtonToggleModule,
    MatFormFieldModule,
    MatInputModule,
    MatRadioModule,
  ],
  template: `
    <div class="fields" [formGroup]="form()">
      @if (showType()) {
        <span class="label">What do you want to cut down?</span>
        <mat-button-toggle-group
          formControlName="type"
          aria-label="Plan type"
          hideSingleSelectionIndicator
        >
          <mat-button-toggle value="smoking">Smoking</mat-button-toggle>
          <mat-button-toggle value="drinking">Drinking</mat-button-toggle>
        </mat-button-toggle-group>
      }
      @let t = form().controls.type.value;
      <mat-form-field>
        <mat-label>How many {{ words[t].units }} {{ words[t].per }} now?</mat-label>
        <input matInput type="number" inputmode="numeric" formControlName="baseline" />
        <mat-hint>Your usual amount. Be honest; the plan starts from here.</mat-hint>
        <mat-error>1 to 100.</mat-error>
      </mat-form-field>
      <span class="label">Pace</span>
      <mat-radio-group formControlName="pace_pct" class="stack" aria-label="Pace">
        <mat-radio-button [value]="5">
          Gentle <span class="hint">5% less each week</span>
        </mat-radio-button>
        <mat-radio-button [value]="10">
          Standard <span class="hint">10% less each week</span>
        </mat-radio-button>
      </mat-radio-group>
    </div>
  `,
  styles: `
    .fields {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .label {
      font: var(--mat-sys-title-small);
      margin-top: 8px;
    }
    .stack {
      display: flex;
      flex-direction: column;
    }
    .hint {
      font: var(--mat-sys-body-small);
      color: var(--mat-sys-on-surface-variant);
      margin-left: 6px;
    }
    mat-button-toggle-group {
      align-self: flex-start;
      margin-bottom: 8px;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HabitSetupComponent {
  readonly form = input.required<HabitForm>();
  readonly showType = input(true);
  protected readonly words = HABIT;
}

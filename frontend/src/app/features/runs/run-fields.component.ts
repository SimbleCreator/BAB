import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { provideNativeDateAdapter } from '@angular/material/core';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { RunForm } from './run-form';

@Component({
  selector: 'app-run-fields',
  imports: [ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatDatepickerModule],
  providers: [provideNativeDateAdapter()],
  template: `
    <div class="fields" [formGroup]="form()">
      <mat-form-field>
        <mat-label>Date</mat-label>
        <input
          matInput
          [matDatepicker]="picker"
          formControlName="day"
          [max]="maxDate()"
          readonly
          (click)="picker.open()"
        />
        <mat-datepicker-toggle matIconSuffix [for]="picker" />
        <mat-datepicker #picker />
        <mat-error>Pick today or an earlier day.</mat-error>
      </mat-form-field>

      <mat-form-field>
        <mat-label>Distance</mat-label>
        <input
          matInput
          type="number"
          inputmode="decimal"
          step="0.01"
          formControlName="distance_km"
        />
        <span matTextSuffix>km</span>
        <mat-error>0.01 to 300 km.</mat-error>
      </mat-form-field>

      <span class="label">Time</span>
      <div class="time" formGroupName="time">
        <mat-form-field subscriptSizing="dynamic">
          <mat-label>h</mat-label>
          <input matInput type="number" inputmode="numeric" formControlName="hours" />
        </mat-form-field>
        <mat-form-field subscriptSizing="dynamic">
          <mat-label>min</mat-label>
          <input matInput type="number" inputmode="numeric" formControlName="minutes" />
        </mat-form-field>
        <mat-form-field subscriptSizing="dynamic">
          <mat-label>s</mat-label>
          <input matInput type="number" inputmode="numeric" formControlName="seconds" />
        </mat-form-field>
      </div>
      @if (form().controls.time.touched && form().controls.time.invalid) {
        <p class="bab-field-error inline">Enter a time between 30 seconds and 48 hours.</p>
      }

      <mat-form-field>
        <mat-label>Note (optional)</mat-label>
        <textarea matInput formControlName="note" rows="2" maxlength="500"></textarea>
      </mat-form-field>
    </div>
  `,
  styles: `
    .fields {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .label {
      font: var(--mat-sys-title-small);
      margin: 4px 0 8px;
    }
    .time {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-bottom: 12px;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RunFieldsComponent {
  readonly form = input.required<RunForm>();
  readonly maxDate = input.required<Date>();
}

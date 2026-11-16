import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { RouterLink } from '@angular/router';

import { apiErrorMessage } from '../../core/api/api-error';
import { CustomFoodOut } from '../../core/api/models';
import { NutritionApi } from '../../core/api/nutrition.api';
import { LoaderComponent } from '../../shared/components/loader.component';

@Component({
  selector: 'app-my-foods-page',
  imports: [
    LoaderComponent,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
  ],
  template: `
    <section class="bab-page">
      <a mat-button routerLink="/eat" class="back"><mat-icon>arrow_back</mat-icon> Eat</a>
      <h1 class="bab-page-title">My foods</h1>
      <p class="bab-muted">
        Foods you added with your own values. Changing one does not change days already logged.
      </p>
      @if (list.isLoading()) {
        <app-loader />
      } @else if (list.error()) {
        <p class="bab-form-error">Could not load your foods.</p>
      } @else if (list.value(); as foods) {
        @if (foods.length === 0) {
          <p class="bab-muted">None yet. Use "Add your own food" when logging a meal.</p>
        }
        @for (f of foods; track f.id) {
          @if (editing() === f.id) {
            <form [formGroup]="form" (ngSubmit)="save(f)" novalidate class="edit">
              <mat-form-field
                ><mat-label>Name</mat-label><input matInput formControlName="name"
              /></mat-form-field>
              <mat-form-field
                ><mat-label>Serving</mat-label><input matInput formControlName="serving_label"
              /></mat-form-field>
              <mat-form-field
                ><mat-label>Grams in one serving (optional)</mat-label
                ><input matInput type="number" formControlName="serving_g" /><mat-hint
                  >Lets you log it by weight</mat-hint
                ><mat-error>1 to 3,000 g.</mat-error></mat-form-field
              >
              <div class="grid">
                <mat-form-field
                  ><mat-label>kcal</mat-label
                  ><input matInput type="number" formControlName="calories_kcal"
                /></mat-form-field>
                <mat-form-field
                  ><mat-label>Protein g</mat-label
                  ><input matInput type="number" formControlName="protein_g"
                /></mat-form-field>
                <mat-form-field
                  ><mat-label>Carbs g</mat-label
                  ><input matInput type="number" formControlName="carbs_g"
                /></mat-form-field>
                <mat-form-field
                  ><mat-label>Fat g</mat-label
                  ><input matInput type="number" formControlName="fat_g"
                /></mat-form-field>
              </div>
              <div class="actions">
                <button mat-flat-button type="submit" [disabled]="busy()">Save</button>
                <button mat-button type="button" (click)="editing.set(null)">Cancel</button>
                <button
                  mat-button
                  type="button"
                  class="danger"
                  (click)="remove(f)"
                  [disabled]="busy()"
                >
                  {{ confirmDelete() === f.id ? 'Tap again to delete' : 'Delete' }}
                </button>
              </div>
            </form>
          } @else {
            <button type="button" class="row" (click)="edit(f)">
              <span>{{ f.name }}</span>
              <span class="bab-muted"
                >{{ f.serving_label }}{{ f.serving_g ? ' (' + f.serving_g + ' g)' : '' }} &middot;
                {{ f.calories_kcal }} kcal</span
              >
            </button>
          }
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
    .row {
      all: unset;
      box-sizing: border-box;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      width: 100%;
      padding: 12px 4px;
      border-bottom: 1px solid var(--mat-sys-outline-variant);
    }
    .edit {
      padding: 12px 0;
      border-bottom: 1px solid var(--mat-sys-outline-variant);
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0 12px;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .danger {
      color: var(--mat-sys-error);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MyFoodsPage {
  private readonly api = inject(NutritionApi);
  private readonly snack = inject(MatSnackBar);
  protected readonly list = rxResource({ stream: () => this.api.customFoods() });
  protected readonly editing = signal<number | null>(null);
  protected readonly confirmDelete = signal<number | null>(null);
  protected readonly busy = signal(false);

  protected readonly form = inject(NonNullableFormBuilder).group({
    name: ['', [Validators.required, Validators.maxLength(80)]],
    serving_label: ['', [Validators.required, Validators.maxLength(40)]],
    serving_g: [null as number | null, [Validators.min(1), Validators.max(3000)]],
    calories_kcal: [0, [Validators.required, Validators.min(0), Validators.max(3000)]],
    protein_g: [0, [Validators.required, Validators.min(0), Validators.max(300)]],
    carbs_g: [0, [Validators.required, Validators.min(0), Validators.max(500)]],
    fat_g: [0, [Validators.required, Validators.min(0), Validators.max(300)]],
  });

  protected edit(f: CustomFoodOut): void {
    this.confirmDelete.set(null);
    this.editing.set(f.id);
    this.form.setValue({
      name: f.name,
      serving_label: f.serving_label,
      serving_g: f.serving_g ?? null,
      calories_kcal: f.calories_kcal,
      protein_g: f.protein_g,
      carbs_g: f.carbs_g,
      fat_g: f.fat_g,
    });
  }

  protected save(f: CustomFoodOut): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    const v = this.form.getRawValue();
    const grams =
      v.serving_g === null || (v.serving_g as unknown) === '' ? null : Number(v.serving_g);
    this.api.updateCustom(f.id, { ...v, serving_g: grams }).subscribe({
      next: () => this.done('Saved.'),
      error: (err: unknown) => this.fail(err),
    });
  }

  protected remove(f: CustomFoodOut): void {
    if (this.confirmDelete() !== f.id) {
      this.confirmDelete.set(f.id);
      return;
    }
    this.busy.set(true);
    this.api.deleteCustom(f.id).subscribe({
      next: () => this.done('Deleted. Days you already logged keep their values.'),
      error: (err: unknown) => this.fail(err),
    });
  }

  private done(message: string): void {
    this.busy.set(false);
    this.editing.set(null);
    this.confirmDelete.set(null);
    this.list.reload();
    this.snack.open(message, undefined, { duration: 2500 });
  }

  private fail(err: unknown): void {
    this.busy.set(false);
    this.snack.open(apiErrorMessage(err), undefined, { duration: 4000 });
  }
}

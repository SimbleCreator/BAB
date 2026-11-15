import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { rxResource, toObservable, toSignal } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router, RouterLink } from '@angular/router';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-error';
import { CustomFoodIn, FoodOut, MealType } from '../../core/api/models';
import { NutritionApi } from '../../core/api/nutrition.api';
import { EstimateBadgeComponent } from '../../shared/components/estimate-badge.component';
import { IntPipe } from '../../shared/format/format.pipes';
import { MEALS, mealForNow } from './meals';

@Component({
  selector: 'app-add-food-page',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatButtonToggleModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatProgressBarModule,
    EstimateBadgeComponent,
    IntPipe,
  ],
  templateUrl: './add-food.page.html',
  styleUrl: './add-food.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AddFoodPage {
  private readonly api = inject(NutritionApi);
  private readonly router = inject(Router);
  private readonly snack = inject(MatSnackBar);

  /** Query parameters. */
  readonly day = input.required<string>();
  readonly meal = input<MealType>();

  protected readonly meals = MEALS;
  protected readonly mealType = signal<MealType | null>(null);
  protected readonly chosenMeal = computed<MealType>(
    () => this.mealType() ?? this.meal() ?? mealForNow(),
  );

  protected readonly typed = signal('');
  private readonly query = toSignal(
    toObservable(this.typed).pipe(debounceTime(250), distinctUntilChanged()),
    { initialValue: '' },
  );
  protected readonly foods = rxResource({
    params: () => ({ q: this.query().trim(), meal: this.chosenMeal() }),
    stream: ({ params }) => this.api.foods(params.q, params.q ? null : params.meal),
  });

  protected readonly picked = signal<FoodOut | null>(null);
  protected readonly servings = signal(1);
  protected readonly preview = computed(() => {
    const f = this.picked();
    const n = this.servings();
    return f
      ? { kcal: Math.round(f.calories_kcal * n), protein: Math.round(f.protein_g * n * 10) / 10 }
      : null;
  });
  protected readonly saving = signal(false);
  protected readonly showCustom = signal(false);

  protected readonly custom = inject(NonNullableFormBuilder).group({
    name: ['', [Validators.required, Validators.maxLength(80), Validators.pattern(/\S/)]],
    serving_label: ['1 serving', [Validators.required, Validators.maxLength(40)]],
    calories_kcal: [
      null as number | null,
      [Validators.required, Validators.min(0), Validators.max(3000)],
    ],
    protein_g: [0, [Validators.required, Validators.min(0), Validators.max(300)]],
    carbs_g: [0, [Validators.required, Validators.min(0), Validators.max(500)]],
    fat_g: [0, [Validators.required, Validators.min(0), Validators.max(300)]],
  });

  protected pick(f: FoodOut): void {
    this.picked.set(f);
    this.servings.set(1);
  }

  protected step(delta: number): void {
    this.servings.update((s) => Math.min(20, Math.max(0.5, Math.round((s + delta) * 2) / 2)));
  }

  protected add(): void {
    const f = this.picked();
    if (!f) return;
    this.saving.set(true);
    this.api
      .addItem(this.day(), {
        meal_type: this.chosenMeal(),
        food_code: f.food_code,
        custom_food_id: f.custom_food_id,
        servings: this.servings(),
      })
      .subscribe({
        next: (d) => {
          this.snack.open(`Added ${f.name}.`, undefined, { duration: 2000 });
          void this.router.navigate(['/eat'], {
            queryParams: { day: d.day === d.today ? null : d.day },
          });
        },
        error: (err: unknown) => {
          this.saving.set(false);
          this.snack.open(apiErrorMessage(err), undefined, { duration: 4000 });
        },
      });
  }

  protected saveCustom(): void {
    if (this.custom.invalid) {
      this.custom.markAllAsTouched();
      return;
    }
    const v = this.custom.getRawValue();
    const body: CustomFoodIn = {
      ...v,
      name: v.name.trim(),
      calories_kcal: Number(v.calories_kcal),
    };
    this.saving.set(true);
    this.api.createCustom(body).subscribe({
      next: (c) => {
        this.saving.set(false);
        this.showCustom.set(false);
        this.custom.reset();
        this.pick({
          kind: 'custom',
          food_code: null,
          custom_food_id: c.id,
          name: c.name,
          serving_label: c.serving_label,
          calories_kcal: c.calories_kcal,
          protein_g: c.protein_g,
          carbs_g: c.carbs_g,
          fat_g: c.fat_g,
          diet_type: null,
          meal_types: [],
          uses: 0,
        });
        this.foods.reload();
      },
      error: (err: unknown) => {
        this.saving.set(false);
        this.snack.open(apiErrorMessage(err), undefined, { duration: 4000 });
      },
    });
  }
}

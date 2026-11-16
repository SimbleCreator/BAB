import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { rxResource, toObservable, toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router, RouterLink } from '@angular/router';
import { concat, debounceTime, distinctUntilChanged, last } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-error';
import { FoodOut, MealType, MessPlateOut } from '../../core/api/models';
import { NutritionApi } from '../../core/api/nutrition.api';
import { EstimateBadgeComponent } from '../../shared/components/estimate-badge.component';
import { MEALS, mealForNow } from './meals';

const MAX_SERVED = 12;

/** Hostel, mess or canteen: tick what was served and get the best plate from it. */
@Component({
  selector: 'app-mess-page',
  imports: [
    RouterLink,
    MatButtonModule,
    MatButtonToggleModule,
    MatIconModule,
    EstimateBadgeComponent,
  ],
  templateUrl: './mess.page.html',
  styleUrl: './mess.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MessPage {
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
  protected readonly max = MAX_SERVED;

  protected readonly typed = signal('');
  private readonly query = toSignal(
    toObservable(this.typed).pipe(debounceTime(250), distinctUntilChanged()),
    { initialValue: '' },
  );
  protected readonly foods = rxResource({
    params: () => ({ q: this.query().trim(), meal: this.chosenMeal() }),
    stream: ({ params }) => this.api.foods(params.q, params.q ? null : params.meal),
  });
  /** Built-in dishes only: the plate is worked out from the food list. */
  protected readonly options = computed(() =>
    (this.foods.value() ?? []).filter((f) => f.kind === 'builtin').slice(0, 30),
  );

  protected readonly served = signal<FoodOut[]>([]);
  protected readonly plate = signal<MessPlateOut | null>(null);
  protected readonly busy = signal(false);

  protected isServed(f: FoodOut): boolean {
    return this.served().some((s) => s.food_code === f.food_code);
  }

  protected toggle(f: FoodOut): void {
    this.plate.set(null);
    if (this.isServed(f)) {
      this.served.update((list) => list.filter((s) => s.food_code !== f.food_code));
    } else if (this.served().length < MAX_SERVED) {
      this.served.update((list) => [...list, f]);
    }
  }

  protected setMeal(m: MealType): void {
    this.mealType.set(m);
    this.plate.set(null);
  }

  protected make(): void {
    const codes = this.served().map((f) => f.food_code!);
    if (!codes.length) return;
    this.busy.set(true);
    this.api.messPlate(this.day(), { meal_type: this.chosenMeal(), food_codes: codes }).subscribe({
      next: (p) => {
        this.busy.set(false);
        this.plate.set(p);
      },
      error: (err: unknown) => {
        this.busy.set(false);
        this.snack.open(apiErrorMessage(err), undefined, { duration: 4000 });
      },
    });
  }

  protected log(): void {
    const p = this.plate();
    if (!p || !p.items.length) return;
    this.busy.set(true);
    concat(
      ...p.items.map((i) =>
        this.api.addItem(this.day(), {
          meal_type: p.meal_type,
          food_code: i.food_code,
          custom_food_id: null,
          grams: i.grams,
        }),
      ),
    )
      .pipe(last())
      .subscribe({
        next: (d) => {
          this.snack.open('Plate logged.', undefined, { duration: 2000 });
          void this.router.navigate(['/eat'], {
            queryParams: { day: d.day === d.today ? null : d.day },
          });
        },
        error: (err: unknown) => {
          this.busy.set(false);
          this.snack.open(apiErrorMessage(err), undefined, { duration: 4000 });
        },
      });
  }
}

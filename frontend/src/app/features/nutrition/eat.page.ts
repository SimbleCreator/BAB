import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router, RouterLink } from '@angular/router';
import { map, of } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-error';
import { DayNutritionOut, ItemOut, MealType, SuggestionOut } from '../../core/api/models';
import { NutritionApi } from '../../core/api/nutrition.api';
import { TodayApi } from '../../core/api/today.api';
import { CaloriesChartComponent } from '../../shared/components/calories-chart.component';
import { EstimateBadgeComponent } from '../../shared/components/estimate-badge.component';
import { addDays, dayLabel } from '../../shared/format/dates';
import { IntPipe } from '../../shared/format/format.pipes';
import { MEALS, servingsLabel } from './meals';
import { LoaderComponent } from '../../shared/components/loader.component';

@Component({
  selector: 'app-eat-page',
  imports: [
    LoaderComponent,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    CaloriesChartComponent,
    EstimateBadgeComponent,
    IntPipe,
  ],
  templateUrl: './eat.page.html',
  styleUrl: './eat.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EatPage {
  private readonly api = inject(NutritionApi);
  private readonly todayApi = inject(TodayApi);
  private readonly router = inject(Router);
  private readonly snack = inject(MatSnackBar);

  /** Query parameter `day` (YYYY-MM-DD). Defaults to the user's today. */
  readonly day = input<string>();

  protected readonly todayRes = rxResource({
    stream: () => this.todayApi.get().pipe(map((t) => t.day)),
  });
  protected readonly selectedDay = computed(() => this.day() ?? this.todayRes.value() ?? null);

  /** The day's data; replaced in place after every add, edit or delete. */
  protected readonly data = rxResource({
    params: () => ({ day: this.selectedDay() }),
    stream: ({ params }) => (params.day ? this.api.day(params.day) : of(null)),
  });
  protected readonly ideas = rxResource({
    params: () => ({ day: this.selectedDay(), eaten: this.data.value()?.eaten.calories_kcal }),
    stream: ({ params }) =>
      params.day && params.eaten !== undefined ? this.api.suggestions(params.day) : of(null),
  });
  protected readonly week = rxResource({ stream: () => this.api.summary(7) });
  protected readonly targets = rxResource({
    params: () => ({ open: this.showHow() }),
    stream: ({ params }) => (params.open ? this.api.targets() : of(null)),
  });

  protected readonly meals = MEALS;
  protected readonly editing = signal<number | null>(null);
  protected readonly editServings = signal(1);
  protected readonly editGrams = signal<number | null>(null);
  protected readonly editGramsValid = computed(() => {
    const g = this.editGrams();
    return g !== null && g >= 1 && g <= 3000;
  });
  protected readonly openIdeas = signal<MealType | null>(null);
  protected readonly showHow = signal(false);
  protected readonly busy = signal(false);

  protected readonly title = computed(() => {
    const d = this.data.value();
    return d ? dayLabel(d.day, d.today) : '';
  });
  protected readonly isToday = computed(() => {
    const d = this.data.value();
    return !!d && d.day === d.today;
  });
  protected readonly percent = computed(() => {
    const d = this.data.value();
    return d
      ? Math.min(100, Math.round((100 * d.eaten.calories_kcal) / d.target.calories_kcal))
      : 0;
  });
  protected readonly macros = computed(() => {
    const d = this.data.value();
    if (!d) return [];
    const row = (label: string, eaten: number, target: number) => ({
      label,
      eaten: Math.round(eaten),
      target,
      pct: target ? Math.min(100, Math.round((100 * eaten) / target)) : 0,
    });
    return [
      row('Protein', d.eaten.protein_g, d.target.protein_g),
      row('Carbs', d.eaten.carbs_g, d.target.carbs_g),
      row('Fat', d.eaten.fat_g, d.target.fat_g),
    ];
  });

  protected readonly servingsLabel = servingsLabel;

  protected mealOf(d: DayNutritionOut, type: MealType) {
    return d.meals.find((m) => m.meal_type === type)!;
  }

  protected ideasFor(type: MealType) {
    return this.ideas.value()?.meals.find((m) => m.meal_type === type) ?? null;
  }

  protected goDay(delta: number): void {
    const d = this.data.value();
    if (!d) return;
    const next = addDays(d.day, delta);
    if (next > d.today) return;
    this.editing.set(null);
    void this.router.navigate(['/eat'], { queryParams: { day: next === d.today ? null : next } });
  }

  protected startEdit(item: ItemOut): void {
    this.editing.set(this.editing() === item.id ? null : item.id);
    this.editServings.set(item.servings);
    this.editGrams.set(item.grams);
  }

  protected setEditGrams(value: string): void {
    const n = Number(value);
    this.editGrams.set(value.trim() === '' || !Number.isFinite(n) ? null : Math.round(n));
  }

  protected stepServings(delta: number): void {
    this.editServings.update((s) => Math.min(20, Math.max(0.5, Math.round((s + delta) * 2) / 2)));
  }

  protected saveEdit(item: ItemOut): void {
    const amount =
      item.grams !== null ? { grams: this.editGrams()! } : { servings: this.editServings() };
    this.run(this.api.updateItem(item.id, amount), 'Updated.');
  }

  protected remove(item: ItemOut): void {
    this.run(this.api.deleteItem(item.id), `Removed ${item.name}.`);
  }

  protected addIdea(type: MealType, s: SuggestionOut): void {
    const d = this.data.value();
    if (!d) return;
    this.run(
      this.api.addItem(d.day, {
        meal_type: type,
        food_code: s.food_code,
        custom_food_id: null,
        grams: s.grams,
      }),
      `Added ${s.name}.`,
    );
  }

  private run(obs: ReturnType<NutritionApi['day']>, message: string): void {
    this.busy.set(true);
    obs.subscribe({
      next: (d) => {
        this.busy.set(false);
        this.editing.set(null);
        this.data.set(d);
        this.week.reload();
        this.snack.open(message, undefined, { duration: 2000 });
      },
      error: (err: unknown) => {
        this.busy.set(false);
        this.snack.open(apiErrorMessage(err), undefined, { duration: 4000 });
      },
    });
  }
}

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  CustomFoodIn,
  CustomFoodOut,
  DayNutritionOut,
  FoodOut,
  ItemIn,
  ItemPatch,
  MealType,
  MessPlateIn,
  MessPlateOut,
  NutritionSummaryOut,
  PlateTipsOut,
  StapleOut,
  SuggestionsOut,
  TargetsOut,
} from './models';

/** Client for the backend `nutrition` router (targets, meals, foods, suggestions). */
@Injectable({ providedIn: 'root' })
export class NutritionApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  targets(): Observable<TargetsOut> {
    return this.http.get<TargetsOut>(`${this.base}/nutrition/targets`);
  }

  day(day: string): Observable<DayNutritionOut> {
    return this.http.get<DayNutritionOut>(`${this.base}/nutrition/days/${day}`);
  }

  addItem(day: string, body: ItemIn): Observable<DayNutritionOut> {
    return this.http.post<DayNutritionOut>(`${this.base}/nutrition/days/${day}/items`, body);
  }

  updateItem(id: number, amount: ItemPatch): Observable<DayNutritionOut> {
    return this.http.patch<DayNutritionOut>(`${this.base}/nutrition/items/${id}`, amount);
  }

  deleteItem(id: number): Observable<DayNutritionOut> {
    return this.http.delete<DayNutritionOut>(`${this.base}/nutrition/items/${id}`);
  }

  suggestions(day: string): Observable<SuggestionsOut> {
    return this.http.get<SuggestionsOut>(`${this.base}/nutrition/days/${day}/suggestions`);
  }

  summary(days = 7): Observable<NutritionSummaryOut> {
    return this.http.get<NutritionSummaryOut>(`${this.base}/nutrition/summary`, {
      params: { days },
    });
  }

  /** Dishes to pick usual home foods from; works before onboarding. Own region first. */
  staples(dietType: string, state: string | null): Observable<StapleOut[]> {
    const params: Record<string, string> = { diet_type: dietType };
    if (state) params['state'] = state;
    return this.http.get<StapleOut[]>(`${this.base}/foods/staples`, { params });
  }

  /** Portion tips for the user's usual home foods. */
  plateTips(): Observable<PlateTipsOut> {
    return this.http.get<PlateTipsOut>(`${this.base}/nutrition/plate-tips`);
  }

  /** Best plate from what the mess served; logs nothing. */
  messPlate(day: string, body: MessPlateIn): Observable<MessPlateOut> {
    return this.http.post<MessPlateOut>(`${this.base}/nutrition/days/${day}/mess-plate`, body);
  }

  foods(q: string, mealType: MealType | null): Observable<FoodOut[]> {
    const params: Record<string, string> = {};
    if (q) params['q'] = q;
    if (mealType) params['meal_type'] = mealType;
    return this.http.get<FoodOut[]>(`${this.base}/foods`, { params });
  }

  customFoods(): Observable<CustomFoodOut[]> {
    return this.http.get<CustomFoodOut[]>(`${this.base}/foods/custom`);
  }

  createCustom(body: CustomFoodIn): Observable<CustomFoodOut> {
    return this.http.post<CustomFoodOut>(`${this.base}/foods/custom`, body);
  }

  updateCustom(id: number, body: CustomFoodIn): Observable<CustomFoodOut> {
    return this.http.put<CustomFoodOut>(`${this.base}/foods/custom/${id}`, body);
  }

  deleteCustom(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/foods/custom/${id}`);
  }
}

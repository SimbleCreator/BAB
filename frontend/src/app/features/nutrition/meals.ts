import { MealType } from '../../core/api/models';

export const MEALS: { type: MealType; label: string; icon: string }[] = [
  { type: 'breakfast', label: 'Breakfast', icon: 'free_breakfast' },
  { type: 'lunch', label: 'Lunch', icon: 'lunch_dining' },
  { type: 'snack', label: 'Snack', icon: 'cookie' },
  { type: 'dinner', label: 'Dinner', icon: 'dinner_dining' },
];

export const MEAL_LABEL: Record<MealType, string> = {
  breakfast: 'Breakfast',
  lunch: 'Lunch',
  snack: 'Snack',
  dinner: 'Dinner',
};

/** A sensible default meal for "quick add", from the device clock. */
export function mealForNow(date = new Date()): MealType {
  const h = date.getHours();
  if (h < 11) return 'breakfast';
  if (h < 16) return 'lunch';
  if (h < 19) return 'snack';
  return 'dinner';
}

export function servingsLabel(servings: number, label: string): string {
  return servings === 1 ? label : `${servings} x ${label}`;
}

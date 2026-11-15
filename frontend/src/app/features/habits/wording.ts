/**
 * All user-facing words for reduction plans live here so the wording rules are easy to
 * review: this is a reduction plan; use is never described as a prize, treat or reward,
 * and nothing encourages it. Over-allowance weeks get no blame.
 */
import { HabitType } from '../../core/api/models';

export const HABIT = {
  smoking: {
    title: 'Smoking',
    unit: 'cigarette',
    units: 'cigarettes',
    per: 'a day',
    logLabel: 'Log a cigarette',
  },
  drinking: {
    title: 'Drinking',
    unit: 'drink',
    units: 'drinks',
    per: 'a week',
    logLabel: 'Log a drink',
  },
} as const;

export function units(type: HabitType, n: number): string {
  return `${n} ${n === 1 ? HABIT[type].unit : HABIT[type].units}`;
}

export const PLAN_INTRO =
  'An optional plan to cut down a little each week. Your allowance shrinks step by step from what you have now.';
export const GOALS_LINE =
  'Each daily goal you complete opens a third of the allowance. The rest stays locked.';
export const OVER_WEEK_LINE =
  'Last week went above the plan, so this week keeps the same allowance. Every week is a fresh start.';
export const ZERO_LINE =
  'Your allowance has reached zero. You have reached the end of the reduction plan.';

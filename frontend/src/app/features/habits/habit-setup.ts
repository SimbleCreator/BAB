import { NonNullableFormBuilder, Validators } from '@angular/forms';

import { HabitIn, HabitType } from '../../core/api/models';

/** Form for starting a plan; used on the Habits page and in onboarding. */
export function buildHabitForm(fb: NonNullableFormBuilder, type: HabitType = 'smoking') {
  return fb.group({
    type: [type as HabitType, Validators.required],
    baseline: [
      null as number | null,
      [Validators.required, Validators.min(1), Validators.max(100)],
    ],
    pace_pct: [5 as 5 | 10, Validators.required],
  });
}

export type HabitForm = ReturnType<typeof buildHabitForm>;

export function habitFromForm(form: HabitForm): HabitIn {
  const v = form.getRawValue();
  return { type: v.type, baseline: Number(v.baseline), pace_pct: v.pace_pct };
}

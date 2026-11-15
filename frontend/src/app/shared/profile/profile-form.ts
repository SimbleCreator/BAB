import { NonNullableFormBuilder, ValidatorFn, Validators } from '@angular/forms';

import { DietType, Goal, Level, ProfileIn, ProfileOut, Sex } from '../../core/api/models';

export const GOAL_OPTIONS: { value: Goal; label: string; hint: string }[] = [
  { value: 'lose_fat', label: 'Lose fat', hint: 'Small calorie deficit, cardio finishers' },
  { value: 'build_muscle', label: 'Build muscle', hint: 'Small surplus, harder variations' },
  { value: 'stay_fit', label: 'Stay fit', hint: 'Maintain weight, all-round training' },
];

export const LEVEL_OPTIONS: { value: Level; label: string; hint: string }[] = [
  { value: 'beginner', label: 'Beginner', hint: 'New to training or back after a long break' },
  { value: 'intermediate', label: 'Intermediate', hint: 'Training regularly for a few months' },
  { value: 'advanced', label: 'Advanced', hint: 'A year or more of steady training' },
];

export const DIET_OPTIONS: { value: DietType; label: string }[] = [
  { value: 'veg', label: 'Veg' },
  { value: 'egg', label: 'Veg + egg' },
  { value: 'non_veg', label: 'Non-veg' },
];

export const SEX_OPTIONS: { value: Sex; label: string }[] = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
];

export const MINUTE_OPTIONS = [20, 30, 40, 50, 60, 90];
export const DAY_OPTIONS = [2, 3, 4, 5, 6];

export const TIMEZONES: string[] = (() => {
  const zones = Intl.supportedValuesOf('timeZone');
  return zones.includes('UTC') ? zones : [...zones, 'UTC'];
})();

export function browserTimezone(): string {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  return TIMEZONES.includes(tz) ? tz : 'UTC';
}

const knownTimezone: ValidatorFn = (c) =>
  TIMEZONES.includes(c.value as string) ? null : { timezone: true };

/** The profile form, shared by onboarding and the account page. Ranges match the API. */
export function buildProfileForm(fb: NonNullableFormBuilder) {
  return fb.group({
    about: fb.group({
      name: ['', [Validators.required, Validators.maxLength(60), Validators.pattern(/\S/)]],
      age: fb.control<number | null>(null, [
        Validators.required,
        Validators.min(18),
        Validators.max(100),
      ]),
      sex: fb.control<Sex | null>(null, Validators.required),
      height_cm: fb.control<number | null>(null, [
        Validators.required,
        Validators.min(120),
        Validators.max(230),
      ]),
      weight_kg: fb.control<number | null>(null, [
        Validators.required,
        Validators.min(30),
        Validators.max(300),
      ]),
    }),
    training: fb.group({
      goal: fb.control<Goal | null>(null, Validators.required),
      level: fb.control<Level | null>(null, Validators.required),
      minutes_per_day: [30, Validators.required],
      days_per_week: [3, Validators.required],
      has_pullup_bar: [false],
    }),
    daily: fb.group({
      diet_type: fb.control<DietType | null>(null, Validators.required),
      daily_step_goal: [8000, [Validators.required, Validators.min(1000), Validators.max(50000)]],
      timezone: [browserTimezone(), [Validators.required, knownTimezone]],
    }),
  });
}

export type ProfileForm = ReturnType<typeof buildProfileForm>;

export function profileFromForm(form: ProfileForm): ProfileIn {
  const { about, training, daily } = form.getRawValue();
  return {
    name: about.name.trim(),
    age: Number(about.age),
    sex: about.sex!,
    height_cm: Number(about.height_cm),
    weight_kg: Number(about.weight_kg),
    goal: training.goal!,
    level: training.level!,
    minutes_per_day: training.minutes_per_day,
    days_per_week: training.days_per_week,
    has_pullup_bar: training.has_pullup_bar,
    diet_type: daily.diet_type!,
    daily_step_goal: Number(daily.daily_step_goal),
    timezone: daily.timezone,
  };
}

export function patchProfileForm(form: ProfileForm, p: ProfileOut): void {
  form.setValue({
    about: {
      name: p.name,
      age: p.age,
      sex: p.sex,
      height_cm: p.height_cm,
      weight_kg: p.weight_kg,
    },
    training: {
      goal: p.goal,
      level: p.level,
      minutes_per_day: p.minutes_per_day,
      days_per_week: p.days_per_week,
      has_pullup_bar: p.has_pullup_bar,
    },
    daily: {
      diet_type: p.diet_type,
      daily_step_goal: p.daily_step_goal,
      timezone: p.timezone,
    },
  });
}

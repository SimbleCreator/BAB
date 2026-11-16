import { NonNullableFormBuilder, ValidatorFn, Validators } from '@angular/forms';

import {
  DietType,
  FoodSource,
  Goal,
  Level,
  ProfileIn,
  ProfileOut,
  Sex,
  TrainingMode,
  WorkType,
} from '../../core/api/models';

export const MODE_OPTIONS: { value: TrainingMode; label: string; hint: string }[] = [
  {
    value: 'activity',
    label: 'Activity',
    hint: 'Walking, jogging and home workouts, no equipment',
  },
  { value: 'gym', label: 'Gym', hint: 'Training at a gym with weights and machines' },
  { value: 'both', label: 'Both', hint: 'Some gym days and some walking, jogging or home days' },
];

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

export const WORK_OPTIONS: { value: WorkType; label: string; hint: string }[] = [
  { value: 'desk', label: 'Desk job', hint: 'Sitting most of the day' },
  { value: 'standing', label: 'On my feet', hint: 'Shop, teaching, nursing, walking around' },
  { value: 'physical', label: 'Physical work', hint: 'Lifting, building, farm or delivery' },
  { value: 'shifts', label: 'Shifts', hint: 'Night or changing hours' },
];

export const FOOD_SOURCE_OPTIONS: { value: FoodSource; label: string }[] = [
  { value: 'home', label: 'Home food' },
  { value: 'hostel', label: 'Hostel or mess' },
  { value: 'out', label: 'Eating out' },
  { value: 'mixed', label: 'A mix' },
];

export const USUAL_FOODS_MAX = 12;

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
      training_mode: fb.control<TrainingMode>('activity', Validators.required),
    }),
    life: fb.group({
      city: ['', [Validators.required, Validators.maxLength(60), Validators.pattern(/\S/)]],
      state: fb.control<string | null>(null, Validators.required),
      work_type: fb.control<WorkType | null>(null, Validators.required),
      food_source: fb.control<FoodSource | null>(null, Validators.required),
      wake_time: ['07:00', [Validators.required, Validators.pattern(/^([01]\d|2[0-3]):[0-5]\d$/)]],
    }),
    plate: fb.group({
      usual_foods: fb.control<string[]>([], Validators.maxLength(USUAL_FOODS_MAX)),
    }),
    more: fb.group({
      sleep_hours: fb.control<number | null>(null, [Validators.min(3), Validators.max(12)]),
      sweet_drinks_per_day: fb.control<number | null>(null, [
        Validators.min(0),
        Validators.max(20),
      ]),
      fasting_note: ['', Validators.maxLength(80)],
      food_budget_inr: fb.control<number | null>(null, [Validators.min(50), Validators.max(5000)]),
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
  const { about, training, daily, life, plate, more } = form.getRawValue();
  const num = (v: number | null) => (v === null || (v as unknown) === '' ? null : Number(v));
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
    training_mode: training.training_mode,
    city: life.city.trim(),
    state: life.state,
    work_type: life.work_type,
    food_source: life.food_source,
    wake_time: life.wake_time,
    usual_foods: plate.usual_foods,
    sleep_hours: num(more.sleep_hours),
    sweet_drinks_per_day: num(more.sweet_drinks_per_day),
    fasting_note: more.fasting_note.trim() || null,
    food_budget_inr: num(more.food_budget_inr),
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
      training_mode: p.training_mode ?? 'activity',
    },
    life: {
      city: p.city ?? '',
      state: p.state ?? null,
      work_type: p.work_type ?? null,
      food_source: p.food_source ?? null,
      wake_time: p.wake_time ?? '07:00',
    },
    plate: { usual_foods: p.usual_foods ?? [] },
    more: {
      sleep_hours: p.sleep_hours ?? null,
      sweet_drinks_per_day: p.sweet_drinks_per_day ?? null,
      fasting_note: p.fasting_note ?? '',
      food_budget_inr: p.food_budget_inr ?? null,
    },
    daily: {
      diet_type: p.diet_type,
      daily_step_goal: p.daily_step_goal,
      timezone: p.timezone,
    },
  });
}

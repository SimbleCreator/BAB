/** Types matching the backend OpenAPI schema (`/openapi.json`). */

export interface HealthOut {
  status: 'ok';
  version: string;
}

export interface ErrorOut {
  detail: string;
  code: string;
}

// auth router ---------------------------------------------------------------

export interface RegisterIn {
  email: string;
  password: string;
  is_adult: boolean;
  accepts_privacy: boolean;
}

export interface LoginIn {
  email: string;
  password: string;
}

export interface ChangePasswordIn {
  current_password: string;
  new_password: string;
}

export interface UserOut {
  id: number;
  email: string;
  is_admin: boolean;
  created_at: string;
  has_profile: boolean;
}

export interface TokenOut {
  access_token: string;
  token_type: 'bearer';
  /** Seconds. */
  expires_in: number;
  user: UserOut;
}

// profile router ------------------------------------------------------------

export type Sex = 'male' | 'female';
export type Goal = 'lose_fat' | 'build_muscle' | 'stay_fit';
export type Level = 'beginner' | 'intermediate' | 'advanced';
export type DietType = 'veg' | 'egg' | 'non_veg';

export interface ProfileIn {
  name: string;
  age: number;
  sex: Sex;
  height_cm: number;
  weight_kg: number;
  goal: Goal;
  level: Level;
  minutes_per_day: number;
  days_per_week: number;
  has_pullup_bar: boolean;
  diet_type: DietType;
  daily_step_goal: number;
  timezone: string;
}

export interface ProfileOut extends ProfileIn {
  updated_at: string;
}

// activity router -----------------------------------------------------------

export type Source = 'manual' | 'csv' | 'gpx' | 'android' | 'ios';

export interface ActivityIn {
  steps: number | null;
  /** Metres. */
  distance_m: number | null;
  active_kcal: number | null;
  note: string | null;
}

export interface ActivityOut {
  /** YYYY-MM-DD, the user's local date. */
  day: string;
  steps: number | null;
  distance_m: number | null;
  active_kcal: number | null;
  distance_estimated: boolean;
  active_kcal_estimated: boolean;
  source: Source;
  note: string | null;
  updated_at: string;
}

export interface DayPoint {
  day: string;
  has_entry: boolean;
  steps: number;
  distance_m: number;
  active_kcal: number;
  goal_met: boolean;
}

export interface ActivitySummaryOut {
  today: string;
  step_goal: number;
  current_streak: number;
  longest_streak: number;
  total_steps: number;
  total_distance_m: number;
  /** Oldest first, ending today. */
  days: DayPoint[];
}

export interface CsvRowOut {
  line: number;
  day: string | null;
  steps: number | null;
  distance_m: number | null;
  active_kcal: number | null;
  errors: string[];
  exists: boolean;
}

export interface CsvPreviewOut {
  file_errors: string[];
  rows: CsvRowOut[];
  valid_rows: number;
  invalid_rows: number;
  existing_rows: number;
}

export interface CsvImportOut {
  created: number;
  updated: number;
  skipped_existing: number;
  skipped_invalid: number;
}

// today router --------------------------------------------------------------

export interface TodayOut {
  day: string;
  name: string;
  line: string;
  step_goal: number;
  current_streak: number;
  activity: ActivityOut | null;
  checkin_due: boolean;
  /** Unlocked but not seen yet. */
  new_milestones: MilestoneBrief[];
  /** Null on a rest day. */
  workout: WorkoutBrief | null;
  nutrition: TodayNutrition;
  /** Active reduction plans; empty if none. */
  habits: TodayHabit[];
}

export interface TodayHabit {
  id: number;
  type: HabitType;
  availability: AvailabilityOut;
}

export interface TodayNutrition {
  target_kcal: number;
  eaten_kcal: number;
  remaining_kcal: number;
  protein_g: number;
  target_protein_g: number;
}

// runs router ---------------------------------------------------------------

export interface RunIn {
  day: string;
  /** Metres. */
  distance_m: number;
  /** Seconds. */
  duration_s: number;
  note: string | null;
}

export type RunPatch = Partial<RunIn>;

export interface RunOut {
  id: number;
  day: string;
  started_at: string | null;
  distance_m: number;
  duration_s: number;
  /** Seconds per km. */
  pace_s_per_km: number | null;
  calories_kcal: number;
  calories_estimated: true;
  source: Source;
  note: string | null;
  has_track: boolean;
  created_at: string;
}

export interface SplitOut {
  km: number;
  distance_m: number;
  duration_s: number;
  pace_s_per_km: number;
}

export interface TrackPointOut {
  lat: number;
  lng: number;
  ele_m: number | null;
}

export interface RunDetailOut extends RunOut {
  splits: SplitOut[];
  track: TrackPointOut[];
}

export interface RunListOut {
  items: RunOut[];
  total: number;
}

// checkins router ------------------------------------------------------------

export interface CheckinIn {
  weight_kg: number;
  waist_cm: number | null;
  chest_cm: number | null;
  arms_cm: number | null;
  thighs_cm: number | null;
  note: string | null;
}

export interface CheckinOut extends CheckinIn {
  day: string;
  /** Change from the previous check-in. */
  weight_change_kg: number | null;
  waist_change_cm: number | null;
}

export interface CheckinStatusOut {
  due: boolean;
  last_day: string | null;
  days_since: number | null;
  today: string;
}

// milestones router ----------------------------------------------------------

export type MilestoneCategory = 'steps' | 'runs' | 'training' | 'food' | 'checkins' | 'habits';
export type MilestoneUnit = 'steps' | 'm' | 'count' | 'days' | 'weeks';

export interface MilestoneOut {
  code: string;
  title: string;
  description: string;
  category: MilestoneCategory;
  target: number;
  current: number;
  unit: MilestoneUnit;
  unlocked_at: string | null;
  seen: boolean;
}

export interface MilestoneBrief {
  code: string;
  title: string;
}

// training router ------------------------------------------------------------

export type Group = 'push' | 'pull' | 'legs' | 'core' | 'cardio';
export type ExerciseType = 'reps' | 'timed';

export interface ExerciseOut {
  code: string;
  name: string;
  group: Group;
  difficulty: number;
  type: ExerciseType;
  needs_bar: boolean;
  easier: string | null;
  harder: string | null;
  instructions: string;
}

export interface DrillOut {
  code: string;
  name: string;
  seconds: number;
  instructions: string;
}

export interface PrescriptionOut {
  code: string;
  name: string;
  group: Group;
  type: ExerciseType;
  sets: number;
  rest_s: number;
  reps_min: number | null;
  reps_max: number | null;
  target_reps: number | null;
  seconds_min: number | null;
  seconds_max: number | null;
  target_seconds: number | null;
}

export interface PlannedSessionOut {
  day: string;
  kind: string;
  title: string;
  focus: Group[];
  warmup: DrillOut[];
  exercises: PrescriptionOut[];
  finisher: PrescriptionOut | null;
  cooldown: DrillOut[];
  est_minutes: number;
}

export type DayStatus = 'rest' | 'planned' | 'not_logged' | 'done' | 'skipped';

export interface PlanDayOut {
  day: string;
  status: DayStatus;
  session: PlannedSessionOut | null;
}

export interface WeekOut {
  week_start: string;
  today: string;
  split: string;
  /** Why the plan last changed, if it did. */
  note: string | null;
  /** Seven days, Monday first. */
  days: PlanDayOut[];
}

export interface SetIn {
  exercise_code: string;
  set_no: number;
  actual_reps: number | null;
  actual_seconds: number | null;
}

export interface WorkoutIn {
  status: 'done' | 'skipped';
  sets: SetIn[];
}

export interface SetOut {
  exercise_code: string;
  set_no: number;
  target_reps: number | null;
  actual_reps: number | null;
  target_seconds: number | null;
  actual_seconds: number | null;
  target_met: boolean;
}

export interface WorkoutSummaryOut {
  sets_planned: number;
  sets_done: number;
  targets_met: number;
  total_reps: number;
  total_seconds: number;
  exercises_skipped: number;
  completion_pct: number;
}

export interface WorkoutOut {
  day: string;
  status: 'done' | 'skipped';
  finished_at: string | null;
  sets: SetOut[];
  summary: WorkoutSummaryOut;
}

export interface WorkoutBrief {
  day: string;
  title: string;
  exercise_count: number;
  est_minutes: number;
  status: DayStatus;
}

// nutrition router -----------------------------------------------------------

export type MealType = 'breakfast' | 'lunch' | 'snack' | 'dinner';

export interface TargetOut {
  effective_from: string;
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  reason: string;
}

export interface TargetBreakdownOut {
  bmr: number;
  activity_factor: number;
  maintenance: number;
  goal_adjustment: number;
  floor: number;
  floor_applied: boolean;
  calories_kcal: number;
}

export interface TargetsOut {
  current: TargetOut;
  breakdown: TargetBreakdownOut;
  history: TargetOut[];
}

export interface FoodOut {
  kind: 'builtin' | 'custom';
  food_code: string | null;
  custom_food_id: number | null;
  name: string;
  serving_label: string;
  /** Per serving, an estimate. */
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  diet_type: string | null;
  meal_types: string[];
  uses: number;
}

export interface CustomFoodIn {
  name: string;
  serving_label: string;
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface CustomFoodOut extends CustomFoodIn {
  id: number;
}

export interface ItemIn {
  meal_type: MealType;
  food_code: string | null;
  custom_food_id: number | null;
  servings: number;
}

export interface ItemOut {
  id: number;
  food_code: string | null;
  custom_food_id: number | null;
  name: string;
  serving_label: string;
  servings: number;
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface Totals {
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface MealOut {
  meal_type: MealType;
  items: ItemOut[];
  totals: Totals;
}

export interface DayNutritionOut {
  day: string;
  today: string;
  target: TargetOut;
  eaten: Totals;
  /** Negative when over. */
  remaining_kcal: number;
  meals: MealOut[];
}

export interface SuggestionOut {
  food_code: string;
  name: string;
  serving_label: string;
  servings: number;
  calories_kcal: number;
  protein_g: number;
}

export interface MealSuggestionsOut {
  meal_type: MealType;
  budget_kcal: number;
  options: SuggestionOut[];
}

export interface SuggestionsOut {
  day: string;
  remaining_kcal: number;
  meals: MealSuggestionsOut[];
}

export interface NutritionDayPoint {
  day: string;
  calories_kcal: number;
  target_kcal: number;
  protein_g: number;
  has_meals: boolean;
}

export interface NutritionSummaryOut {
  days: NutritionDayPoint[];
}

// weekly adjustment ----------------------------------------------------------

export interface NutritionChangeOut {
  before_kcal: number;
  after_kcal: number;
  change_kcal: number;
  floor_applied: boolean;
  reason: string;
}

export interface TrainingChangeOut {
  decision: 'progress' | 'reduce' | 'unchanged' | 'no_data';
  planned_sessions: number;
  done_sessions: number;
  completion_pct: number;
  changes: string[];
  summary: string;
}

export interface AdjustmentOut {
  id: number;
  checkin_day: string;
  reference_day: string;
  created_at: string;
  /** + gain / - loss per week, % of body weight. */
  weekly_change_pct: number;
  nutrition: NutritionChangeOut;
  training: TrainingChangeOut;
  summary: string[];
}

export interface CheckinSavedOut extends CheckinOut {
  adjustment: AdjustmentOut | null;
  adjustment_note: string | null;
}

// habits router --------------------------------------------------------------

export type HabitType = 'smoking' | 'drinking';

export interface HabitIn {
  type: HabitType;
  /** Cigarettes per day, or drinks per week. */
  baseline: number;
  pace_pct: 5 | 10;
}

export interface HabitOut {
  id: number;
  type: HabitType;
  period: 'day' | 'week';
  baseline: number;
  pace_pct: number;
  started_on: string;
  active: boolean;
}

export interface GoalsOut {
  steps: boolean;
  workout: boolean;
  meals: boolean;
  met: number;
}

export interface AvailabilityOut {
  period: 'day' | 'week';
  allowance: number;
  unlocked: number;
  available_now: number;
  locked: number;
  used: number;
  over: number;
}

export interface WeekResultOut {
  number: number;
  start: string;
  end: string;
  step: number;
  allowance_total: number;
  used: number;
  within: boolean;
  avoided: number;
}

export interface HabitStatusOut {
  habit: HabitOut;
  today: string;
  week_number: number;
  week_start: string;
  week_end: string;
  allowance_per_period: number;
  week_allowance: number;
  week_used: number;
  today_used: number;
  availability: AvailabilityOut;
  goals_today: GoalsOut;
  last_week: WeekResultOut | null;
  doctor_line: string;
}

export interface DayLogOut {
  day: string;
  units: number;
}

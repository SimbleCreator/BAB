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
/** activity: walk, jog, home workouts. gym: gym training. both: the user does both. */
export type TrainingMode = 'activity' | 'gym' | 'both';

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
  training_mode: TrainingMode;
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

// history router -------------------------------------------------------------

export interface MonthDayOut {
  day: string;
  activity: boolean;
  workout: 'done' | 'skipped' | null;
  meals: boolean;
  checkin: boolean;
  runs: number;
}

export interface MonthOut {
  /** YYYY-MM */
  month: string;
  today: string;
  days: MonthDayOut[];
}

export interface HabitDayOut {
  habit_id: number;
  type: HabitType;
  units: number;
}

export interface HistoryDayOut {
  day: string;
  today: string;
  activity: ActivityOut | null;
  runs: RunOut[];
  workout_title: string | null;
  workout: WorkoutOut | null;
  nutrition: DayNutritionOut;
  checkin: CheckinOut | null;
  habits: HabitDayOut[];
}

// account router -------------------------------------------------------------

export interface DeleteAccountIn {
  password: string;
  confirm: true;
}

export interface PublicConfigOut {
  app_name: string;
  contact_email: string;
  version: string;
}

export interface WeekCount {
  week_start: string;
  count: number;
}

export interface AdminStatsOut {
  total_users: number;
  active_7_days: number;
  active_30_days: number;
  new_users_per_week: WeekCount[];
  records: Record<string, number>;
}

// bounce router -------------------------------------------------------------

export type BounceDay = 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun';
export type BouncePlanState = 'disabled' | 'none' | 'active' | 'checkin_needed' | 'update_ready';
export type GymExperience = 'beginner' | 'intermediate' | 'advanced';
export type SupplementCode =
  | 'none'
  | 'whey_protein'
  | 'creatine'
  | 'pre_workout'
  | 'multivitamin'
  | 'omega_3'
  | 'bcaa'
  | 'mass_gainer'
  | 'fat_burner'
  | 'other';

export interface BounceExercise {
  name: string;
  sets: number;
  reps: number | null;
  seconds: number | null;
  rest_s: number | null;
  notes: string | null;
}

export interface BounceStretch {
  name: string;
  seconds: number;
}

export interface BouncePlanDay {
  day: BounceDay;
  rest: boolean;
  walk_minutes: number;
  jog_minutes: number;
  steps_target: number;
  home_exercises: BounceExercise[];
  gym_focus: string | null;
  gym_exercises: BounceExercise[];
  cardio_minutes: number;
  stretching: BounceStretch[];
}

export interface BounceMealDay {
  day: BounceDay;
  breakfast: string;
  lunch: string;
  snack: string;
  dinner: string;
}

export interface BounceDiet {
  principles: string[];
  eat_more: string[];
  limit: string[];
  days: BounceMealDay[];
}

export interface BouncePlanContent {
  summary: string;
  days: BouncePlanDay[];
  diet: BounceDiet;
  supplements_advice: string[];
  tips: string[];
}

export interface BounceTargets {
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface BouncePlanOut {
  id: number;
  created_at: string;
  week_start: string;
  mode: TrainingMode;
  model: string;
  based_on_checkin_day: string | null;
  /** From the nutrition engine, not the model. */
  targets: BounceTargets;
  content: BouncePlanContent;
}

export interface BounceNotificationOut {
  /** Stable per day and reason; the app hides it once dismissed. */
  id: string;
  kind: 'checkin' | 'meals' | 'activity';
  title: string;
  message: string;
  action_label: string;
}

export interface BounceStatusOut {
  enabled: boolean;
  mode: TrainingMode;
  state: BouncePlanState;
  gym_profile_needed: boolean;
  plan_created_at: string | null;
  next_update_on: string | null;
  plans_left_today: number;
  /** True when asking for a new plan would be accepted. */
  can_generate: boolean;
  message: string;
  /** Immediate suggestions for today. */
  tips: string[];
  /** The one thing Bounce wants the user to do now, if any. */
  notification: BounceNotificationOut | null;
}

export interface GymProfileIn {
  experience: GymExperience;
  days_per_week: number;
  session_minutes: number;
  supplements: SupplementCode[];
  supplements_note: string | null;
  injuries_note: string | null;
}

export interface GymProfileOut extends GymProfileIn {
  updated_at: string;
}

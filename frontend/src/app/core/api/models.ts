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

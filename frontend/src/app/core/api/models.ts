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

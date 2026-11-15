import { GymExperience, SupplementCode, TrainingMode } from '../../core/api/models';

export const MODE_LABEL: Record<TrainingMode, string> = {
  activity: 'Activity',
  gym: 'Gym',
  both: 'Activity + Gym',
};

export const EXPERIENCE_OPTIONS: { value: GymExperience; label: string; hint: string }[] = [
  { value: 'beginner', label: 'Beginner', hint: 'Under 6 months of lifting' },
  { value: 'intermediate', label: 'Intermediate', hint: '6 months to 2 years' },
  { value: 'advanced', label: 'Advanced', hint: 'More than 2 years' },
];

export const SUPPLEMENT_OPTIONS: { value: SupplementCode; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'whey_protein', label: 'Whey protein' },
  { value: 'creatine', label: 'Creatine' },
  { value: 'pre_workout', label: 'Pre-workout' },
  { value: 'multivitamin', label: 'Multivitamin' },
  { value: 'omega_3', label: 'Omega-3 / fish oil' },
  { value: 'bcaa', label: 'BCAA' },
  { value: 'mass_gainer', label: 'Mass gainer' },
  { value: 'fat_burner', label: 'Fat burner' },
  { value: 'other', label: 'Other' },
];

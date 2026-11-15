import { PrescriptionOut } from '../../core/api/models';

/** "3 x 12-15 reps" or "3 x 30 s". */
export function targetLine(p: PrescriptionOut): string {
  if (p.target_seconds !== null) return `${p.sets} x ${p.target_seconds} s`;
  const range = p.reps_min === p.reps_max ? `${p.reps_min}` : `${p.reps_min}-${p.reps_max}`;
  return `${p.sets} x ${range} reps`;
}

export const GROUP_LABEL: Record<string, string> = {
  push: 'Push',
  pull: 'Pull',
  legs: 'Legs',
  core: 'Core',
  cardio: 'Cardio',
};

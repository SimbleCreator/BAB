import {
  AbstractControl,
  NonNullableFormBuilder,
  ValidationErrors,
  Validators,
} from '@angular/forms';

import { RunDetailOut, RunIn } from '../../core/api/models';
import { formatDay, parseDay } from '../../shared/format/dates';

const MIN_S = 30;
const MAX_S = 48 * 3600;

const durationRange = (g: AbstractControl): ValidationErrors | null => {
  const { hours, minutes, seconds } = g.value as Record<string, number | null>;
  const total = (Number(hours) || 0) * 3600 + (Number(minutes) || 0) * 60 + (Number(seconds) || 0);
  return total < MIN_S || total > MAX_S ? { duration: true } : null;
};

/** Manual run form, shared by "add run" and "edit run". Limits match the API. */
export function buildRunForm(fb: NonNullableFormBuilder, today: Date) {
  return fb.group({
    day: fb.control<Date>(today, Validators.required),
    distance_km: fb.control<number | null>(null, [
      Validators.required,
      Validators.min(0.01),
      Validators.max(300),
    ]),
    time: fb.group(
      {
        hours: fb.control<number | null>(null, [Validators.min(0), Validators.max(48)]),
        minutes: fb.control<number | null>(null, [Validators.min(0), Validators.max(59)]),
        seconds: fb.control<number | null>(null, [Validators.min(0), Validators.max(59)]),
      },
      { validators: durationRange },
    ),
    note: fb.control('', Validators.maxLength(500)),
  });
}

export type RunForm = ReturnType<typeof buildRunForm>;

export function runFromForm(form: RunForm): RunIn {
  const v = form.getRawValue();
  const t = v.time;
  return {
    day: formatDay(v.day),
    distance_m: Math.round(Number(v.distance_km) * 1000),
    duration_s:
      (Number(t.hours) || 0) * 3600 + (Number(t.minutes) || 0) * 60 + (Number(t.seconds) || 0),
    note: v.note.trim() || null,
  };
}

export function patchRunForm(form: RunForm, run: RunDetailOut): void {
  const s = run.duration_s;
  form.setValue({
    day: parseDay(run.day),
    distance_km: run.distance_m / 1000,
    time: { hours: Math.floor(s / 3600), minutes: Math.floor((s % 3600) / 60), seconds: s % 60 },
    note: run.note ?? '',
  });
}

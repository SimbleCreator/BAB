import { Pipe, PipeTransform } from '@angular/core';

import { dayLabel } from './dates';

const INT = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
const KM = new Intl.NumberFormat(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 });

/** 12345 -> "12,345". Null -> "-". */
@Pipe({ name: 'int' })
export class IntPipe implements PipeTransform {
  transform(value: number | null | undefined): string {
    return value === null || value === undefined ? '-' : INT.format(value);
  }
}

/** Metres -> "6.2 km". */
@Pipe({ name: 'km' })
export class KmPipe implements PipeTransform {
  transform(metres: number | null | undefined): string {
    return metres === null || metres === undefined ? '-' : `${KM.format(metres / 1000)} km`;
  }
}

/** API day -> "Today", "Yesterday" or "Mon, 3 Mar". */
@Pipe({ name: 'dayLabel' })
export class DayLabelPipe implements PipeTransform {
  transform(day: string, today: string): string {
    return dayLabel(day, today);
  }
}

export function formatDuration(totalSeconds: number): string {
  const s = Math.max(0, Math.round(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const mm = h ? String(m).padStart(2, '0') : String(m);
  return `${h ? `${h}:` : ''}${mm}:${String(sec).padStart(2, '0')}`;
}

/** Seconds -> "1:02:03" or "45:07". */
@Pipe({ name: 'duration' })
export class DurationPipe implements PipeTransform {
  transform(seconds: number | null | undefined): string {
    return seconds === null || seconds === undefined ? '-' : formatDuration(seconds);
  }
}

/** Seconds per km -> "5:30 /km". */
@Pipe({ name: 'pace' })
export class PacePipe implements PipeTransform {
  transform(secondsPerKm: number | null | undefined): string {
    return secondsPerKm ? `${formatDuration(secondsPerKm)} /km` : '-';
  }
}

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

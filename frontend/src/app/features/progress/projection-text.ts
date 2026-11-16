import { ProjectionOut } from '../../core/api/models';
import { parseDay } from '../../shared/format/dates';

const DATE = new Intl.DateTimeFormat(undefined, {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
});
const KG = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });

export interface ProjectionText {
  /** Big line, e.g. "11 to 16 weeks". */
  headline: string;
  /** e.g. "Around 2 Feb to 9 Mar 2027 to reach 60 kg (4.5 kg to go)." */
  detail: string;
  /** Where the number comes from. */
  basis: string | null;
  /** Encouragement or a caution. */
  note: string | null;
  caution: boolean;
}

export function kg(v: number): string {
  return `${KG.format(v)} kg`;
}

/** Words for the projection. All rules live in the API; this only formats them. */
export function projectionText(p: ProjectionOut): ProjectionText {
  const target = p.target_kg !== null ? kg(p.target_kg) : '';
  const toGo = p.kg_to_go !== null ? kg(Math.abs(p.kg_to_go)) : '';
  const rate = p.weekly_rate_kg !== null ? kg(Math.abs(p.weekly_rate_kg)) : '';
  const direction = (p.kg_to_go ?? 0) < 0 ? 'down' : 'up';
  switch (p.status) {
    case 'no_target':
      return {
        headline: 'Set a target weight',
        detail: 'Add one in Account and B.A.B shows how long it could take.',
        basis: null,
        note: null,
        caution: false,
      };
    case 'reached':
      return {
        headline: 'You are there',
        detail: `You are at your target of ${target}. Hold it, or set a new one.`,
        basis: null,
        note: 'Holding a weight is a skill too. Keep the habits that got you here.',
        caution: false,
      };
    case 'no_gap':
      return {
        headline: 'No date yet',
        detail: `Your calorie target keeps your weight about steady, so it will not move you ${direction} to ${target}.`,
        basis: 'Check that your goal in Account matches your target weight.',
        note: null,
        caution: true,
      };
    case 'stalled':
      return {
        headline: 'Holding steady',
        detail: `Your check-ins show your weight is not moving ${direction} right now (${toGo} to go to ${target}).`,
        basis: 'Based on your recent check-ins.',
        note: 'Plateaus are normal. Keep logging and checking in weekly; your plan adjusts to get you moving again.',
        caution: false,
      };
    case 'on_track': {
      const weeks =
        p.weeks_min === p.weeks_max
          ? `About ${p.weeks_min} weeks`
          : `${p.weeks_min} to ${p.weeks_max} weeks`;
      const dates =
        p.date_min && p.date_max
          ? p.date_min === p.date_max
            ? `around ${DATE.format(parseDay(p.date_min))}`
            : `between ${DATE.format(parseDay(p.date_min))} and ${DATE.format(parseDay(p.date_max))}`
          : '';
      const basis =
        p.method === 'trend'
          ? `Based on your check-ins: about ${rate} ${direction} a week.`
          : `Based on your calorie target: about ${rate} ${direction} a week.` +
            (p.checkins_for_trend > 0
              ? ` After ${p.checkins_for_trend} more check-in${p.checkins_for_trend === 1 ? '' : 's'} it uses your real trend.`
              : '');
      return {
        headline: weeks,
        detail: `To reach ${target} (${toGo} to go), ${dates}.`,
        basis,
        note: p.too_fast
          ? `That is faster than the safe pace of about ${kg(p.safe_rate_kg)} a week. Eat enough and do not rush it.`
          : 'Stick with your plan and this is within reach. Every week counts.',
        caution: p.too_fast,
      };
    }
  }
}

import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

import { ActivityApi } from '../../core/api/activity.api';
import { CheckinsApi } from '../../core/api/checkins.api';
import { MilestonesApi } from '../../core/api/milestones.api';
import { HabitType } from '../../core/api/models';
import { NutritionApi } from '../../core/api/nutrition.api';
import { TodayApi } from '../../core/api/today.api';
import { TrainingApi } from '../../core/api/training.api';
import { CaloriesChartComponent } from '../../shared/components/calories-chart.component';
import { EstimateBadgeComponent } from '../../shared/components/estimate-badge.component';
import { LoaderComponent } from '../../shared/components/loader.component';
import { ProgressRingComponent } from '../../shared/components/progress-ring.component';
import { StepsChartComponent } from '../../shared/components/steps-chart.component';
import { CountUpDirective } from '../../shared/directives/count-up.directive';
import { WeightChartComponent } from '../../shared/components/weight-chart.component';
import { IntPipe, KmPipe } from '../../shared/format/format.pipes';
import { HABIT } from '../habits/wording';
import { mealForNow } from '../nutrition/meals';

const DATE = new Intl.DateTimeFormat(undefined, { weekday: 'long', day: 'numeric', month: 'long' });

interface QuickAction {
  label: string;
  icon: string;
  link: string;
  query?: Record<string, string>;
  gradient: string;
}

@Component({
  selector: 'app-home-page',
  imports: [
    RouterLink,
    MatButtonModule,
    MatIconModule,
    LoaderComponent,
    ProgressRingComponent,
    StepsChartComponent,
    CaloriesChartComponent,
    WeightChartComponent,
    EstimateBadgeComponent,
    IntPipe,
    KmPipe,
    CountUpDirective,
  ],
  templateUrl: './home.page.html',
  styleUrl: './home.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HomePage {
  private readonly todayApi = inject(TodayApi);
  private readonly activityApi = inject(ActivityApi);
  private readonly nutritionApi = inject(NutritionApi);
  private readonly trainingApi = inject(TrainingApi);
  private readonly checkinsApi = inject(CheckinsApi);
  private readonly milestonesApi = inject(MilestonesApi);

  protected readonly today = rxResource({ stream: () => this.todayApi.get() });
  protected readonly steps = rxResource({ stream: () => this.activityApi.summary(7) });
  protected readonly food = rxResource({ stream: () => this.nutritionApi.summary(7) });
  protected readonly week = rxResource({ stream: () => this.trainingApi.week() });
  protected readonly checkins = rxResource({ stream: () => this.checkinsApi.list() });
  protected readonly milestones = rxResource({ stream: () => this.milestonesApi.list() });

  protected readonly mealNow = mealForNow;

  protected readonly greeting = computed(() => {
    const h = new Date().getHours();
    return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  });

  protected readonly dateLabel = computed(() => {
    const t = this.today.value();
    if (!t) return '';
    const [y, m, d] = t.day.split('-').map(Number);
    return DATE.format(new Date(y, m - 1, d));
  });

  protected readonly todaySteps = computed(() => this.today.value()?.activity?.steps ?? 0);

  protected readonly weekStats = computed(() => {
    const s = this.steps.value();
    const f = this.food.value();
    const w = this.week.value();
    const fedDays = f?.days.filter((d) => d.has_meals) ?? [];
    const planned = w?.days.filter((d) => d.session) ?? [];
    return {
      steps: s?.total_steps ?? 0,
      distance: s?.total_distance_m ?? 0,
      goalDays: s?.days.filter((d) => d.goal_met).length ?? 0,
      avgKcal: fedDays.length
        ? Math.round(fedDays.reduce((n, d) => n + d.calories_kcal, 0) / fedDays.length)
        : 0,
      workoutsDone: planned.filter((d) => d.status === 'done').length,
      workoutsPlanned: planned.length,
    };
  });

  /** Today's mission: four simple daily goals, all from data the server already gave us. */
  protected readonly mission = computed(() => {
    const t = this.today.value();
    if (!t) return null;
    const steps = (t.activity?.steps ?? 0) >= t.step_goal;
    const workoutDone = !t.workout || t.workout.status === 'done';
    const food = t.nutrition.eaten_kcal > 0;
    const checkin = !t.checkin_due;
    const items = [
      {
        done: steps,
        icon: 'directions_walk',
        label: `Hit ${new Intl.NumberFormat().format(t.step_goal)} steps`,
        link: ['/activity/day', t.day],
        query: { back: '/home' } as Record<string, string>,
        gradient: 'var(--bab-grad-steps)',
      },
      {
        done: workoutDone,
        icon: 'fitness_center',
        label: t.workout ? `Finish ${t.workout.title.toLowerCase()}` : 'Rest and recover',
        link: t.workout ? ['/train/workout', t.workout.day] : ['/train'],
        query: null,
        gradient: 'var(--bab-grad-train)',
      },
      {
        done: food,
        icon: 'restaurant',
        label: 'Log what you eat',
        link: ['/eat/add'],
        query: { day: t.day, meal: mealForNow() } as Record<string, string>,
        gradient: 'var(--bab-grad-food)',
      },
      {
        done: checkin,
        icon: 'monitor_weight',
        label: checkin ? 'Check-in up to date' : 'Do your weekly check-in',
        link: ['/checkin'],
        query: null,
        gradient: 'var(--bab-grad-checkin)',
      },
    ];
    const done = items.filter((i) => i.done).length;
    return { items, done, pct: Math.round((100 * done) / items.length) };
  });

  protected readonly missionLine = computed(() => {
    const m = this.mission();
    if (!m) return '';
    if (m.done === 4) return 'Beast mode. Everything done today.';
    if (m.done === 3) return 'One more and the day is yours.';
    if (m.done >= 1) return 'Good start. Keep stacking wins.';
    return 'Four small wins make a strong day.';
  });

  /** The last seven days of the step goal, oldest first. */
  protected readonly streakDots = computed(() =>
    (this.steps.value()?.days ?? []).map((d) => ({
      day: d.day,
      met: d.goal_met,
      label: new Intl.DateTimeFormat(undefined, { weekday: 'narrow' }).format(
        new Date(d.day + 'T00:00:00'),
      ),
    })),
  );

  protected readonly weightPoints = computed(() => [...(this.checkins.value() ?? [])].reverse());
  protected readonly latestCheckin = computed(() => this.checkins.value()?.[0] ?? null);

  /** The locked milestone that is closest to done. */
  protected readonly nextMilestone = computed(() => {
    const locked = (this.milestones.value() ?? []).filter((m) => !m.unlocked_at && m.current > 0);
    return (
      locked.sort((a, b) => b.current / b.target - a.current / a.target)[0] ??
      (this.milestones.value() ?? []).find((m) => !m.unlocked_at) ??
      null
    );
  });
  protected readonly unlockedCount = computed(
    () => (this.milestones.value() ?? []).filter((m) => m.unlocked_at).length,
  );

  protected readonly milestoneTitles = computed(() =>
    (this.today.value()?.new_milestones ?? []).map((m) => m.title).join(', '),
  );

  protected readonly quickActions = computed<QuickAction[]>(() => {
    const day = this.today.value()?.day ?? '';
    const actions: QuickAction[] = [
      {
        label: 'Log steps',
        icon: 'directions_walk',
        link: `/activity/day/${day}`,
        query: { back: '/home' },
        gradient: 'var(--bab-grad-steps)',
      },
      {
        label: 'Add food',
        icon: 'restaurant',
        link: '/eat/add',
        query: { day, meal: mealForNow() },
        gradient: 'var(--bab-grad-food)',
      },
      { label: 'Train', icon: 'fitness_center', link: '/train', gradient: 'var(--bab-grad-train)' },
      {
        label: 'Add run',
        icon: 'directions_run',
        link: '/runs/new',
        gradient: 'var(--bab-grad-run)',
      },
      {
        label: 'Check in',
        icon: 'monitor_weight',
        link: '/checkin',
        gradient: 'var(--bab-grad-checkin)',
      },
      {
        label: 'History',
        icon: 'calendar_month',
        link: '/history',
        gradient: 'var(--bab-grad-habit)',
      },
    ];
    return actions;
  });

  protected milestonePct(current: number, target: number): number {
    return target ? Math.min(100, Math.round((100 * current) / target)) : 0;
  }

  protected milestoneProgress(m: { current: number; target: number; unit: string }): string {
    const fmt = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
    if (m.unit === 'm')
      return `${fmt.format(m.current / 1000)} of ${fmt.format(m.target / 1000)} km`;
    const unit =
      m.unit === 'steps'
        ? ' steps'
        : m.unit === 'days'
          ? ' days'
          : m.unit === 'weeks'
            ? ' weeks'
            : '';
    return `${fmt.format(m.current)} of ${fmt.format(m.target)}${unit}`;
  }

  protected habitTitle(type: HabitType): string {
    return HABIT[type].title;
  }

  protected change(v: number | null): string {
    if (v === null || v === undefined) return '';
    if (v === 0) return 'no change';
    return `${v > 0 ? '+' : ''}${v.toFixed(1)} kg`;
  }
}

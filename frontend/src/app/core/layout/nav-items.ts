export interface NavItem {
  path: string;
  label: string;
  icon: string;
  /** Gradient for the item's tile in the More sheet. */
  gradient?: string;
  hint?: string;
}

/** The floating dock: the four places people go every day. */
export const PRIMARY_NAV: readonly NavItem[] = [
  { path: '/home', label: 'Home', icon: 'space_dashboard' },
  { path: '/activity', label: 'Activity', icon: 'directions_walk' },
  { path: '/train', label: 'Train', icon: 'fitness_center' },
  { path: '/eat', label: 'Eat', icon: 'restaurant' },
];

/** Everything else, shown as colourful tiles in the More sheet. */
export const MORE_NAV: readonly NavItem[] = [
  {
    path: '/runs',
    label: 'Runs',
    icon: 'directions_run',
    gradient: 'var(--bab-grad-run)',
    hint: 'Routes and pace',
  },
  {
    path: '/progress',
    label: 'Progress',
    icon: 'trending_down',
    gradient: 'var(--bab-grad-checkin)',
    hint: 'Your goal and 4-week cards',
  },
  {
    path: '/checkin',
    label: 'Check-in',
    icon: 'monitor_weight',
    gradient: 'var(--bab-grad-checkin)',
    hint: 'Weekly weigh-in',
  },
  {
    path: '/milestones',
    label: 'Milestones',
    icon: 'military_tech',
    gradient: 'var(--bab-grad-hero)',
    hint: 'Your wins',
  },
  {
    path: '/habits',
    label: 'Habits',
    icon: 'trending_down',
    gradient: 'var(--bab-grad-habit)',
    hint: 'Cut down plan',
  },
  {
    path: '/history',
    label: 'History',
    icon: 'calendar_month',
    gradient: 'var(--bab-grad-sky)',
    hint: 'Every day logged',
  },
  {
    path: '/account',
    label: 'Account',
    icon: 'person',
    gradient: 'var(--bab-grad-train)',
    hint: 'Profile and data',
  },
];

export const ADMIN_NAV: NavItem = {
  path: '/admin',
  label: 'Admin',
  icon: 'admin_panel_settings',
  gradient: 'linear-gradient(135deg, #1d1534, #4f46e5)',
  hint: 'Totals only',
};

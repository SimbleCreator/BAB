export interface NavItem {
  path: string;
  label: string;
  icon: string;
}

/** Bottom navigation on phones. */
export const PRIMARY_NAV: readonly NavItem[] = [
  { path: '/today', label: 'Today', icon: 'today' },
  { path: '/activity', label: 'Activity', icon: 'directions_walk' },
  { path: '/train', label: 'Train', icon: 'fitness_center' },
  { path: '/eat', label: 'Eat', icon: 'restaurant' },
];

/** Items inside "More" on phones; listed directly in the side rail on desktop. */
export const MORE_NAV: readonly NavItem[] = [
  { path: '/runs', label: 'Runs', icon: 'directions_run' },
  { path: '/checkin', label: 'Check-in', icon: 'monitor_weight' },
  { path: '/milestones', label: 'Milestones', icon: 'military_tech' },
  { path: '/habits', label: 'Habits', icon: 'trending_down' },
  { path: '/history', label: 'History', icon: 'calendar_month' },
  { path: '/account', label: 'Account', icon: 'person' },
];

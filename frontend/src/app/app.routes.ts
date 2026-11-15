import { Routes } from '@angular/router';

const upcoming = () =>
  import('./shared/components/upcoming-page.component').then((m) => m.UpcomingPageComponent);

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'today' },
  {
    path: 'today',
    title: 'Today - B.A.B',
    loadComponent: () => import('./features/today/today.page').then((m) => m.TodayPage),
  },
  {
    path: 'activity',
    title: 'Activity - B.A.B',
    loadComponent: upcoming,
    data: {
      title: 'Activity',
      icon: 'directions_walk',
      blurb: 'Log steps, distance and active calories for any day.',
    },
  },
  {
    path: 'train',
    title: 'Train - B.A.B',
    loadComponent: upcoming,
    data: {
      title: 'Train',
      icon: 'fitness_center',
      blurb: 'Your weekly bodyweight plan and workout log.',
    },
  },
  {
    path: 'eat',
    title: 'Eat - B.A.B',
    loadComponent: upcoming,
    data: {
      title: 'Eat',
      icon: 'restaurant',
      blurb: 'Daily calorie and protein targets with meal logging.',
    },
  },
  {
    path: 'more',
    title: 'More - B.A.B',
    loadComponent: () => import('./features/more/more.page').then((m) => m.MorePage),
  },
  {
    path: 'runs',
    title: 'Runs - B.A.B',
    loadComponent: upcoming,
    data: {
      title: 'Runs',
      icon: 'directions_run',
      blurb: 'Add runs by hand or from a GPX file, with a route map.',
    },
  },
  {
    path: 'checkin',
    title: 'Check-in - B.A.B',
    loadComponent: upcoming,
    data: { title: 'Check-in', icon: 'monitor_weight', blurb: 'Weekly weight and measurements.' },
  },
  {
    path: 'milestones',
    title: 'Milestones - B.A.B',
    loadComponent: upcoming,
    data: {
      title: 'Milestones',
      icon: 'military_tech',
      blurb: 'Targets you unlock as you keep going.',
    },
  },
  {
    path: 'habits',
    title: 'Habits - B.A.B',
    loadComponent: upcoming,
    data: {
      title: 'Habits',
      icon: 'trending_down',
      blurb: 'An optional plan to cut down on smoking or drinking.',
    },
  },
  {
    path: 'history',
    title: 'History - B.A.B',
    loadComponent: upcoming,
    data: {
      title: 'History',
      icon: 'calendar_month',
      blurb: 'A calendar of everything you have logged.',
    },
  },
  {
    path: 'account',
    title: 'Account - B.A.B',
    loadComponent: upcoming,
    data: {
      title: 'Account',
      icon: 'person',
      blurb: 'Profile, password, data export and account removal.',
    },
  },
  { path: '**', redirectTo: 'today' },
];

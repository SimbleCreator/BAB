import { Routes } from '@angular/router';

import { authGuard, guestGuard, onboardingGuard, profileGuard } from './core/auth/guards';

const upcoming = () =>
  import('./shared/components/upcoming-page.component').then((m) => m.UpcomingPageComponent);

export const routes: Routes = [
  // Public pages
  {
    path: 'login',
    title: 'Sign in - B.A.B',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/login.page').then((m) => m.LoginPage),
  },
  {
    path: 'register',
    title: 'Create account - B.A.B',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/register.page').then((m) => m.RegisterPage),
  },
  {
    path: 'privacy',
    title: 'Privacy - B.A.B',
    loadComponent: upcoming,
    data: {
      title: 'Privacy policy',
      icon: 'policy',
      blurb: 'The full privacy policy is published here before launch.',
    },
  },
  {
    path: 'terms',
    title: 'Terms - B.A.B',
    loadComponent: upcoming,
    data: {
      title: 'Terms of use',
      icon: 'gavel',
      blurb: 'The terms of use are published here before launch.',
    },
  },

  // Signed in, profile not set up yet
  {
    path: 'onboarding',
    title: 'Set up - B.A.B',
    canActivate: [authGuard, onboardingGuard],
    loadComponent: () =>
      import('./features/onboarding/onboarding.page').then((m) => m.OnboardingPage),
  },

  // The app
  {
    path: '',
    canActivate: [authGuard, profileGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'today' },
      {
        path: 'today',
        title: 'Today - B.A.B',
        loadComponent: () => import('./features/today/today.page').then((m) => m.TodayPage),
      },
      {
        path: 'activity',
        title: 'Activity - B.A.B',
        loadComponent: () =>
          import('./features/activity/activity.page').then((m) => m.ActivityPage),
      },
      {
        path: 'activity/day/:day',
        title: 'Log a day - B.A.B',
        loadComponent: () => import('./features/activity/day-edit.page').then((m) => m.DayEditPage),
      },
      {
        path: 'activity/import',
        title: 'Import CSV - B.A.B',
        loadComponent: () => import('./features/activity/import.page').then((m) => m.ImportPage),
      },
      {
        path: 'train',
        title: 'Train - B.A.B',
        loadComponent: () => import('./features/training/train.page').then((m) => m.TrainPage),
      },
      {
        path: 'train/workout/:day',
        title: 'Workout - B.A.B',
        loadComponent: () => import('./features/training/workout.page').then((m) => m.WorkoutPage),
      },
      {
        path: 'train/exercises',
        title: 'Exercises - B.A.B',
        loadComponent: () =>
          import('./features/training/exercises.page').then((m) => m.ExercisesPage),
      },
      {
        path: 'train/exercises/:code',
        title: 'Exercise - B.A.B',
        loadComponent: () =>
          import('./features/training/exercise-detail.page').then((m) => m.ExerciseDetailPage),
      },
      {
        path: 'eat',
        title: 'Eat - B.A.B',
        loadComponent: () => import('./features/nutrition/eat.page').then((m) => m.EatPage),
      },
      {
        path: 'eat/add',
        title: 'Add food - B.A.B',
        loadComponent: () =>
          import('./features/nutrition/add-food.page').then((m) => m.AddFoodPage),
      },
      {
        path: 'eat/foods',
        title: 'My foods - B.A.B',
        loadComponent: () =>
          import('./features/nutrition/my-foods.page').then((m) => m.MyFoodsPage),
      },
      {
        path: 'more',
        title: 'More - B.A.B',
        loadComponent: () => import('./features/more/more.page').then((m) => m.MorePage),
      },
      {
        path: 'runs',
        title: 'Runs - B.A.B',
        loadComponent: () => import('./features/runs/runs.page').then((m) => m.RunsPage),
      },
      {
        path: 'runs/new',
        title: 'Add run - B.A.B',
        loadComponent: () => import('./features/runs/run-new.page').then((m) => m.RunNewPage),
      },
      {
        path: 'runs/:id',
        title: 'Run - B.A.B',
        loadComponent: () => import('./features/runs/run-detail.page').then((m) => m.RunDetailPage),
      },
      {
        path: 'runs/:id/edit',
        title: 'Edit run - B.A.B',
        loadComponent: () => import('./features/runs/run-edit.page').then((m) => m.RunEditPage),
      },
      {
        path: 'checkin',
        title: 'Check-in - B.A.B',
        loadComponent: () => import('./features/checkin/checkin.page').then((m) => m.CheckinPage),
      },
      {
        path: 'milestones',
        title: 'Milestones - B.A.B',
        loadComponent: () =>
          import('./features/milestones/milestones.page').then((m) => m.MilestonesPage),
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
        loadComponent: () => import('./features/account/account.page').then((m) => m.AccountPage),
      },
    ],
  },
  { path: '**', redirectTo: 'today' },
];

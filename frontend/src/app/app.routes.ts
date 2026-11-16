import { Routes } from '@angular/router';

import {
  adminGuard,
  authGuard,
  guestGuard,
  onboardingGuard,
  profileGuard,
} from './core/auth/guards';

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
    loadComponent: () => import('./features/legal/privacy.page').then((m) => m.PrivacyPage),
  },
  {
    path: 'terms',
    title: 'Terms - B.A.B',
    loadComponent: () => import('./features/legal/terms.page').then((m) => m.TermsPage),
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
      { path: '', pathMatch: 'full', redirectTo: 'home' },
      {
        path: 'home',
        title: 'Home - B.A.B',
        loadComponent: () => import('./features/home/home.page').then((m) => m.HomePage),
      },
      { path: 'today', pathMatch: 'full', redirectTo: 'home' },
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
        path: 'progress',
        title: 'Progress - B.A.B',
        loadComponent: () =>
          import('./features/progress/progress.page').then((m) => m.ProgressPage),
      },
      {
        path: 'bounce',
        title: 'Bounce - B.A.B',
        loadComponent: () => import('./features/bounce/bounce.page').then((m) => m.BouncePage),
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
        loadComponent: () => import('./features/habits/habits.page').then((m) => m.HabitsPage),
      },
      {
        path: 'history',
        title: 'History - B.A.B',
        loadComponent: () => import('./features/history/history.page').then((m) => m.HistoryPage),
      },
      {
        path: 'admin',
        title: 'Admin - B.A.B',
        canActivate: [adminGuard],
        loadComponent: () => import('./features/admin/admin.page').then((m) => m.AdminPage),
      },
      {
        path: 'account',
        title: 'Account - B.A.B',
        loadComponent: () => import('./features/account/account.page').then((m) => m.AccountPage),
      },
    ],
  },
  { path: '**', redirectTo: 'home' },
];

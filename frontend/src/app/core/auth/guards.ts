import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';

/** Signed-in users only. */
export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  if (auth.isLoggedIn()) return true;
  return inject(Router).createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};

/** Login and register pages: skip them when already signed in. */
export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.isLoggedIn() ? inject(Router).createUrlTree(['/home']) : true;
};

/** App pages need a finished onboarding. */
export const profileGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.hasProfile() ? true : inject(Router).createUrlTree(['/onboarding']);
};

/** Onboarding only until it is done. */
export const onboardingGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.hasProfile() ? inject(Router).createUrlTree(['/home']) : true;
};

/** Admin pages: admins only. */
export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.user()?.is_admin ? true : inject(Router).createUrlTree(['/home']);
};

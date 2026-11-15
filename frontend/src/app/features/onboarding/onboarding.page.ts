import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatStepperModule } from '@angular/material/stepper';
import { Router } from '@angular/router';
import { concat, last, of } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-error';
import { HabitsApi } from '../../core/api/habits.api';
import { ProfileApi } from '../../core/api/profile.api';
import { AuthService } from '../../core/auth/auth.service';
import { ProfileFieldsComponent } from '../../shared/profile/profile-fields.component';
import { buildProfileForm, profileFromForm } from '../../shared/profile/profile-form';
import { buildHabitForm, habitFromForm } from '../habits/habit-setup';
import { HabitSetupComponent } from '../habits/habit-setup.component';
import { PLAN_INTRO } from '../habits/wording';

@Component({
  selector: 'app-onboarding-page',
  imports: [
    ReactiveFormsModule,
    MatStepperModule,
    MatButtonModule,
    MatCheckboxModule,
    ProfileFieldsComponent,
    HabitSetupComponent,
  ],
  templateUrl: './onboarding.page.html',
  styleUrl: './onboarding.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OnboardingPage {
  private readonly profileApi = inject(ProfileApi);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  private readonly habitsApi = inject(HabitsApi);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly form = buildProfileForm(this.fb);
  protected readonly intro = PLAN_INTRO;
  protected readonly wantSmoking = signal(false);
  protected readonly wantDrinking = signal(false);
  protected readonly smokingForm = buildHabitForm(this.fb, 'smoking');
  protected readonly drinkingForm = buildHabitForm(this.fb, 'drinking');
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);

  protected finish(): void {
    const habitForms = [
      ...(this.wantSmoking() ? [this.smokingForm] : []),
      ...(this.wantDrinking() ? [this.drinkingForm] : []),
    ];
    if (this.form.invalid || habitForms.some((f) => f.invalid)) {
      this.form.markAllAsTouched();
      habitForms.forEach((f) => f.markAllAsTouched());
      return;
    }
    this.pending.set(true);
    this.error.set(null);
    // Profile first (plans need it), then any reduction plans.
    concat(
      this.profileApi.save(profileFromForm(this.form)),
      ...habitForms.map((f) => this.habitsApi.start(habitFromForm(f))),
      of(null),
    )
      .pipe(last())
      .subscribe({
        next: () => {
          this.auth.markProfileComplete();
          void this.router.navigateByUrl('/home');
        },
        error: (err: unknown) => {
          this.pending.set(false);
          this.error.set(apiErrorMessage(err));
        },
      });
  }

  protected logout(): void {
    this.auth.logout().subscribe();
  }
}

import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatStepperModule } from '@angular/material/stepper';
import { Router } from '@angular/router';

import { apiErrorMessage } from '../../core/api/api-error';
import { ProfileApi } from '../../core/api/profile.api';
import { AuthService } from '../../core/auth/auth.service';
import { ProfileFieldsComponent } from '../../shared/profile/profile-fields.component';
import { buildProfileForm, profileFromForm } from '../../shared/profile/profile-form';

@Component({
  selector: 'app-onboarding-page',
  imports: [ReactiveFormsModule, MatStepperModule, MatButtonModule, ProfileFieldsComponent],
  templateUrl: './onboarding.page.html',
  styleUrl: './onboarding.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OnboardingPage {
  private readonly profileApi = inject(ProfileApi);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly form = buildProfileForm(inject(NonNullableFormBuilder));
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);

  protected finish(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.pending.set(true);
    this.error.set(null);
    this.profileApi.save(profileFromForm(this.form)).subscribe({
      next: () => {
        this.auth.markProfileComplete();
        void this.router.navigateByUrl('/today');
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

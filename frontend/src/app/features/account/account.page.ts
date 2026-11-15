import { ChangeDetectionStrategy, Component, effect, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';

import { apiErrorMessage } from '../../core/api/api-error';
import { ProfileApi } from '../../core/api/profile.api';
import { AuthService } from '../../core/auth/auth.service';
import { PASSWORD_MIN } from '../auth/register.page';
import { ProfileFieldsComponent } from '../../shared/profile/profile-fields.component';
import {
  buildProfileForm,
  patchProfileForm,
  profileFromForm,
} from '../../shared/profile/profile-form';

@Component({
  selector: 'app-account-page',
  imports: [
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    ProfileFieldsComponent,
  ],
  templateUrl: './account.page.html',
  styleUrl: './account.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AccountPage {
  private readonly profileApi = inject(ProfileApi);
  private readonly snack = inject(MatSnackBar);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly auth = inject(AuthService);

  protected readonly profile = rxResource({ stream: () => this.profileApi.get() });
  protected readonly form = buildProfileForm(this.fb);
  protected readonly saving = signal(false);
  protected readonly profileError = signal<string | null>(null);

  protected readonly passwordMin = PASSWORD_MIN;
  protected readonly pwForm = this.fb.group({
    current_password: ['', Validators.required],
    new_password: [
      '',
      [Validators.required, Validators.minLength(PASSWORD_MIN), Validators.maxLength(128)],
    ],
  });
  protected readonly pwSaving = signal(false);
  protected readonly pwError = signal<string | null>(null);

  constructor() {
    effect(() => {
      const p = this.profile.value();
      if (p) {
        patchProfileForm(this.form, p);
        this.form.markAsPristine();
      }
    });
  }

  /** Set when a save would rebuild the training plan; the user must confirm first. */
  protected readonly confirmPlanChange = signal(false);

  private planFieldsChanged(): boolean {
    const p = this.profile.value();
    if (!p) return false;
    const next = profileFromForm(this.form);
    return (
      p.goal !== next.goal ||
      p.level !== next.level ||
      p.minutes_per_day !== next.minutes_per_day ||
      p.days_per_week !== next.days_per_week ||
      p.has_pullup_bar !== next.has_pullup_bar
    );
  }

  protected saveProfile(confirmed = false): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    if (!confirmed && this.planFieldsChanged()) {
      this.confirmPlanChange.set(true);
      return;
    }
    this.confirmPlanChange.set(false);
    this.saving.set(true);
    this.profileError.set(null);
    this.profileApi.save(profileFromForm(this.form)).subscribe({
      next: (p) => {
        this.saving.set(false);
        this.profile.set(p);
        this.snack.open('Profile saved.', undefined, { duration: 2500 });
      },
      error: (err: unknown) => {
        this.saving.set(false);
        this.profileError.set(apiErrorMessage(err));
      },
    });
  }

  protected changePassword(): void {
    if (this.pwForm.invalid) {
      this.pwForm.markAllAsTouched();
      return;
    }
    this.pwSaving.set(true);
    this.pwError.set(null);
    this.auth.changePassword(this.pwForm.getRawValue()).subscribe({
      next: () => {
        this.pwSaving.set(false);
        this.pwForm.reset();
        this.snack.open('Password changed. Other devices were signed out.', undefined, {
          duration: 3500,
        });
      },
      error: (err: unknown) => {
        this.pwSaving.set(false);
        this.pwError.set(apiErrorMessage(err));
      },
    });
  }

  protected logout(): void {
    this.auth.logout().subscribe();
  }
}

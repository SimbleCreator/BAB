import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatRadioModule } from '@angular/material/radio';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import {
  DAY_OPTIONS,
  DIET_OPTIONS,
  GOAL_OPTIONS,
  LEVEL_OPTIONS,
  MINUTE_OPTIONS,
  ProfileForm,
  SEX_OPTIONS,
  TIMEZONES,
} from './profile-form';

type Section = 'about' | 'training' | 'daily';

/** Renders one section of the shared profile form. */
@Component({
  selector: 'app-profile-fields',
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatRadioModule,
    MatButtonToggleModule,
    MatSlideToggleModule,
    MatAutocompleteModule,
  ],
  templateUrl: './profile-fields.component.html',
  styleUrl: './profile-fields.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProfileFieldsComponent {
  readonly form = input.required<ProfileForm>();
  readonly section = input.required<Section>();

  protected readonly goals = GOAL_OPTIONS;
  protected readonly levels = LEVEL_OPTIONS;
  protected readonly diets = DIET_OPTIONS;
  protected readonly sexes = SEX_OPTIONS;
  protected readonly minutes = MINUTE_OPTIONS;
  protected readonly days = DAY_OPTIONS;

  protected readonly group = computed(() => this.form().controls[this.section()] as FormGroup);

  protected readonly tzQuery = signal('');

  protected readonly tzMatches = computed(() => {
    const q = this.tzQuery().toLowerCase().replace(/\s+/g, '_');
    const hits = q ? TIMEZONES.filter((z) => z.toLowerCase().includes(q)) : TIMEZONES;
    return hits.slice(0, 50);
  });
}

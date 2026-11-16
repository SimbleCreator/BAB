import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  signal,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatRadioModule } from '@angular/material/radio';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import { of } from 'rxjs';

import { ProfileApi } from '../../core/api/profile.api';
import {
  DAY_OPTIONS,
  DIET_OPTIONS,
  FOOD_SOURCE_OPTIONS,
  GOAL_OPTIONS,
  LEVEL_OPTIONS,
  MINUTE_OPTIONS,
  MODE_OPTIONS,
  ProfileForm,
  SEX_OPTIONS,
  TIMEZONES,
  WORK_OPTIONS,
} from './profile-form';
import { UsualFoodsPickerComponent } from './usual-foods-picker.component';

type Section = 'about' | 'training' | 'daily' | 'life' | 'plate' | 'more';

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
    UsualFoodsPickerComponent,
  ],
  templateUrl: './profile-fields.component.html',
  styleUrl: './profile-fields.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProfileFieldsComponent {
  private readonly profileApi = inject(ProfileApi);

  readonly form = input.required<ProfileForm>();
  readonly section = input.required<Section>();

  protected readonly works = WORK_OPTIONS;
  protected readonly foodSources = FOOD_SOURCE_OPTIONS;

  /** States and union territories, only fetched for the "Your day" section. */
  protected readonly options = rxResource({
    params: () => this.section() === 'life',
    stream: ({ params }) => (params ? this.profileApi.options() : of(null)),
  });

  /** Diet and state, kept current so the dish picker follows edits in other sections. */
  protected readonly dietType = signal<string | null>(null);
  protected readonly state = signal<string | null>(null);
  protected readonly usualControl = computed(
    () => this.form().controls.plate.controls.usual_foods as FormControl<string[]>,
  );

  constructor() {
    effect((onCleanup) => {
      const f = this.form();
      const sync = () => {
        const v = f.getRawValue();
        this.dietType.set(v.daily.diet_type);
        this.state.set(v.life.state);
      };
      sync();
      const sub = f.valueChanges.subscribe(sync);
      onCleanup(() => sub.unsubscribe());
    });
  }

  protected readonly goals = GOAL_OPTIONS;
  protected readonly modes = MODE_OPTIONS;
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

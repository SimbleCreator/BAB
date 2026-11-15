import { ChangeDetectionStrategy, Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

import { publicConfigResource } from './legal';

@Component({
  selector: 'app-privacy-page',
  imports: [RouterLink, MatButtonModule, MatIconModule],
  template: `
    <article class="bab-page legal">
      <h1 class="bab-page-title">Privacy policy</h1>
      <p class="placeholder">
        <mat-icon>edit_note</mat-icon>
        PLACEHOLDER TEXT FOR THE OWNER TO REVIEW. Have this checked before launch, for example
        against the data protection law that applies where your users live.
      </p>

      <h2>What we store</h2>
      <ul>
        <li>
          Your account: email address, a scrambled (hashed) password, when you agreed to this policy
          and when you last signed in.
        </li>
        <li>
          Your profile: name, age, sex, height, weight, goal, training preferences, diet type, step
          goal and timezone.
        </li>
        <li>
          What you log: daily steps, distance and calories; runs and GPS tracks from files you
          upload; workouts; meals and your own foods; weekly check-ins and measurements; and, if you
          use one, your smoking or drinking reduction plan.
        </li>
        <li>
          What the app works out from that: training plans, calorie targets, weekly adjustments and
          milestones.
        </li>
      </ul>
      <p>
        We do not store body photos, uploaded GPX files (only the processed track) or your location
        outside runs you upload.
      </p>

      <h2>Why</h2>
      <p>
        Only to run B.A.B for you: to build your plans, show your progress and keep your data
        between devices. We do not use it for advertising and we do not run third-party analytics.
      </p>

      <h2>Sharing</h2>
      <p>
        Your data is not sold or shared with anyone. It is kept on the servers that run the app. Map
        tiles are loaded from OpenStreetMap, which sees the map area you view but not your account.
      </p>

      <h2>Export and delete</h2>
      <p>
        You can download everything stored about you as one file, and delete your account and all of
        its data permanently, from
        <a routerLink="/account">Account</a>. Deletion cannot be undone.
      </p>

      <h2>Health information</h2>
      <p>
        Numbers in B.A.B are estimates only and not medical advice. Talk to a doctor before big
        changes to diet or exercise.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about your data:
        @if (config.value(); as c) {
          <a [href]="'mailto:' + c.contact_email">{{ c.contact_email }}</a>
        } @else {
          the contact email shown here once it loads.
        }
      </p>
      <p class="bab-muted"><a routerLink="/terms">Terms of use</a></p>
    </article>
  `,
  styleUrl: './legal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PrivacyPage {
  protected readonly config = publicConfigResource();
}

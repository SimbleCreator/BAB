import { ChangeDetectionStrategy, Component } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

import { publicConfigResource } from './legal';

@Component({
  selector: 'app-terms-page',
  imports: [RouterLink, MatIconModule],
  template: `
    <article class="bab-page legal">
      <h1 class="bab-page-title">Terms of use</h1>
      <p class="placeholder">
        <mat-icon>edit_note</mat-icon>
        PLACEHOLDER TEXT FOR THE OWNER TO REVIEW before launch.
      </p>
      <h2>Who can use B.A.B</h2>
      <p>
        You must be 18 or older. Keep your password private; you are responsible for activity on
        your account.
      </p>
      <h2>Not medical advice</h2>
      <p>
        Training plans, calorie targets, food values and reduction plans are general estimates. They
        are not medical advice and do not replace a doctor, dietitian or trainer. Stop any exercise
        that causes pain and get help if you feel unwell.
      </p>
      <h2>Your content</h2>
      <p>
        What you log stays yours. You can export it or delete it at any time from Account. See the
        <a routerLink="/privacy">privacy policy</a>.
      </p>
      <h2>The service</h2>
      <p>
        B.A.B is provided as it is. Features may change. We may suspend accounts that misuse the
        service.
      </p>
      <h2>Contact</h2>
      <p>
        @if (config.value(); as c) {
          <a [href]="'mailto:' + c.contact_email">{{ c.contact_email }}</a>
        }
      </p>
    </article>
  `,
  styleUrl: './legal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TermsPage {
  protected readonly config = publicConfigResource();
}

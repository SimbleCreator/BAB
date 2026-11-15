import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { MORE_NAV } from '../../core/layout/nav-items';

@Component({
  selector: 'app-more-page',
  imports: [MatListModule, MatIconModule, RouterLink],
  template: `
    <section class="bab-page">
      <h1 class="bab-page-title">More</h1>
      <mat-nav-list>
        @for (item of items; track item.path) {
          <a mat-list-item [routerLink]="item.path">
            <mat-icon matListItemIcon>{{ item.icon }}</mat-icon>
            <span matListItemTitle>{{ item.label }}</span>
          </a>
        }
        @if (auth.user()?.is_admin) {
          <a mat-list-item routerLink="/admin">
            <mat-icon matListItemIcon>admin_panel_settings</mat-icon>
            <span matListItemTitle>Admin</span>
          </a>
        }
      </mat-nav-list>
      <p class="links bab-muted">
        <a routerLink="/privacy">Privacy</a> &middot; <a routerLink="/terms">Terms</a>
      </p>
    </section>
  `,
  styles: `
    .links {
      padding: 16px;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MorePage {
  protected readonly items = MORE_NAV;
  protected readonly auth = inject(AuthService);
}

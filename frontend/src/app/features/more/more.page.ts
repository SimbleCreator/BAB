import { ChangeDetectionStrategy, Component } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { RouterLink } from '@angular/router';

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
      </mat-nav-list>
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MorePage {
  protected readonly items = MORE_NAV;
}

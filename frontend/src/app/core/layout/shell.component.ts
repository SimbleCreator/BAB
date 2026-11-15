import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter, map } from 'rxjs';

import { AuthService } from '../auth/auth.service';
import { MORE_NAV, PRIMARY_NAV } from './nav-items';

@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, MatToolbarModule, MatIconModule],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShellComponent {
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);

  protected readonly primaryNav = PRIMARY_NAV;
  protected readonly moreNav = MORE_NAV;

  private readonly url = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => e.urlAfterRedirects),
    ),
    { initialValue: this.router.url },
  );

  /** Navigation shows only inside the app, not on sign-in or onboarding pages. */
  protected readonly showNav = computed(() => {
    const url = this.url();
    return this.auth.hasProfile() && !/^\/(login|register|onboarding)\b/.test(url);
  });

  /** "More" is highlighted on the More page and on every page it holds. */
  protected readonly moreActive = computed(() => {
    const url = this.url();
    return url.startsWith('/more') || this.moreNav.some((i) => url.startsWith(i.path));
  });
}

import { A11yModule } from '@angular/cdk/a11y';
import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  computed,
  effect,
  inject,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatIconModule } from '@angular/material/icon';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter, map } from 'rxjs';

import { BounceBallComponent } from '../../shared/components/bounce-ball.component';
import { AuthService } from '../auth/auth.service';
import { BounceMascotComponent } from './bounce-mascot.component';
import { MoreTilesComponent } from './more-tiles.component';
import { MORE_NAV, PRIMARY_NAV } from './nav-items';

@Component({
  selector: 'app-shell',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatIconModule,
    A11yModule,
    MoreTilesComponent,
    BounceBallComponent,
    BounceMascotComponent,
  ],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShellComponent {
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);

  protected readonly primaryNav = PRIMARY_NAV;
  protected readonly mascot = viewChild(BounceMascotComponent);
  private prevUrl: string | null = null;
  protected readonly sheetOpen = signal(false);

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

  /** "More" lights up on the More page and on every section it holds. */
  protected readonly moreActive = computed(() => {
    const url = this.url();
    return (
      this.sheetOpen() ||
      url.startsWith('/more') ||
      url.startsWith('/admin') ||
      MORE_NAV.some((i) => url.startsWith(i.path))
    );
  });

  constructor() {
    // Coming back to Home (or opening the app on it): Bounce bounces in to the dock key.
    effect(() => {
      const url = this.url();
      const show = this.showNav();
      untracked(() => {
        const was = this.prevUrl;
        this.prevUrl = url;
        if (!show) return;
        const home = url.startsWith('/home');
        if (home && !was?.startsWith('/home')) {
          setTimeout(() => this.mascot()?.arrive(), 400);
        } else if (was === null) {
          setTimeout(() => this.mascot()?.refresh(), 400);
        }
      });
    });
  }

  protected readonly initial = computed(() =>
    (this.auth.user()?.email ?? '?').charAt(0).toUpperCase(),
  );

  protected toggleSheet(): void {
    this.sheetOpen.update((v) => !v);
  }

  @HostListener('document:keydown.escape')
  protected close(): void {
    this.sheetOpen.set(false);
  }
}

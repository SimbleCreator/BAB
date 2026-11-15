import { ChangeDetectionStrategy, Component, computed, inject, output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

import { AuthService } from '../auth/auth.service';
import { ADMIN_NAV, MORE_NAV } from './nav-items';

/** Colourful tiles for every section outside the dock. Used by the More sheet and page. */
@Component({
  selector: 'app-more-tiles',
  imports: [RouterLink, MatIconModule],
  template: `
    <div class="tiles">
      @for (item of items(); track item.path; let i = $index) {
        <a
          class="tile"
          [routerLink]="item.path"
          (click)="picked.emit()"
          [style.--d]="i * 40 + 'ms'"
        >
          <span class="icon" [style.background]="item.gradient"
            ><mat-icon>{{ item.icon }}</mat-icon></span
          >
          <span class="label">{{ item.label }}</span>
          <span class="hint">{{ item.hint }}</span>
        </a>
      }
    </div>
    <div class="foot">
      <a routerLink="/privacy" (click)="picked.emit()">Privacy</a>
      <span aria-hidden="true">&middot;</span>
      <a routerLink="/terms" (click)="picked.emit()">Terms</a>
      <span class="spacer"></span>
      <button type="button" class="signout" (click)="signOut()">
        <mat-icon>logout</mat-icon>
        Sign out
      </button>
    </div>
  `,
  styles: `
    .tiles {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }
    .tile {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 6px;
      padding: 14px 12px;
      border-radius: 20px;
      background: #fff;
      border: 1px solid var(--bab-border);
      box-shadow: 0 6px 18px rgba(40, 24, 80, 0.07);
      color: var(--bab-text);
      text-decoration: none;
      animation: pop 0.45s var(--d, 0ms) cubic-bezier(0.22, 1.4, 0.36, 1) both;
      transition:
        transform 0.15s ease,
        box-shadow 0.2s ease;
    }
    .tile:hover {
      transform: translateY(-3px);
      box-shadow: var(--bab-shadow-lift);
    }
    .tile:active {
      transform: scale(0.97);
    }
    .icon {
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      border-radius: 14px;
      color: #fff;
      box-shadow: 0 8px 18px rgba(40, 24, 80, 0.18);
    }
    .label {
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-family: var(--bab-font-display);
      font-weight: 800;
      font-size: 0.95rem;
    }
    .hint {
      font-size: 0.78rem;
      color: var(--bab-text-dim);
    }
    .foot {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 16px;
      font-size: 0.9rem;
      color: var(--bab-text-dim);
    }
    .foot a {
      color: var(--bab-text-dim);
    }
    .spacer {
      flex: 1;
    }
    .signout {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 14px;
      border: 1px solid var(--bab-border-strong);
      border-radius: 999px;
      background: #fff;
      color: var(--bab-text);
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    @media (min-width: 640px) {
      .tiles {
        grid-template-columns: repeat(4, 1fr);
      }
    }
    @keyframes pop {
      from {
        transform: translateY(12px) scale(0.96);
      }
      to {
        transform: none;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MoreTilesComponent {
  private readonly auth = inject(AuthService);
  readonly picked = output<void>();
  protected readonly items = computed(() =>
    this.auth.user()?.is_admin ? [...MORE_NAV, ADMIN_NAV] : MORE_NAV,
  );

  protected signOut(): void {
    this.picked.emit();
    this.auth.logout().subscribe();
  }
}

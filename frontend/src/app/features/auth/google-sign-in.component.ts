import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  NgZone,
  OnDestroy,
  inject,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { RouterLink } from '@angular/router';

import { apiErrorCode, apiErrorMessage } from '../../core/api/api-error';
import { AuthApi } from '../../core/api/auth.api';
import { UserOut } from '../../core/api/models';
import { AuthService } from '../../core/auth/auth.service';

const GIS_SRC = 'https://accounts.google.com/gsi/client';

/** The small part of Google Identity Services this component uses. */
interface GoogleIdApi {
  initialize(config: {
    client_id: string;
    callback: (r: { credential: string }) => void;
    ux_mode?: 'popup';
    context?: 'signin' | 'signup' | 'use';
    itp_support?: boolean;
  }): void;
  renderButton(el: HTMLElement, options: Record<string, unknown>): void;
  cancel(): void;
}
declare global {
  interface Window {
    google?: { accounts: { id: GoogleIdApi } };
  }
}

let gisLoading: Promise<void> | null = null;

function loadGis(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  gisLoading ??= new Promise<void>((resolve, reject) => {
    const s = document.createElement('script');
    s.src = GIS_SRC;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => {
      gisLoading = null;
      reject(new Error('gis'));
    };
    document.head.appendChild(s);
  });
  return gisLoading;
}

/** Shows the email from a Google ID token (display only; the server verifies it). */
function emailFromToken(credential: string): string | null {
  try {
    const part = credential.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return (JSON.parse(atob(part)) as { email?: string }).email ?? null;
  } catch {
    return null;
  }
}

/**
 * "Continue with Google". Hidden when the server has no Google client id. A new Google
 * user confirms 18+ and the privacy policy here before the account is created.
 */
@Component({
  selector: 'app-google-sign-in',
  imports: [MatButtonModule, MatCheckboxModule, RouterLink],
  template: `
    @if (enabled()) {
      @if (pendingCredential()) {
        <div class="consent" role="group" aria-label="Create your account with Google">
          <p>
            Create your B.A.B account
            @if (pendingEmail(); as e) {
              for <strong>{{ e }}</strong>
            }
          </p>
          <mat-checkbox [checked]="adult()" (change)="adult.set($event.checked)">
            I am 18 or older
          </mat-checkbox>
          <mat-checkbox [checked]="privacy()" (change)="privacy.set($event.checked)">
            I agree to the <a routerLink="/privacy" target="_blank">privacy policy</a>
          </mat-checkbox>
          <div class="actions">
            <button
              mat-flat-button
              type="button"
              [disabled]="!adult() || !privacy() || busy()"
              (click)="send(true)"
            >
              {{ busy() ? 'Creating...' : 'Create account' }}
            </button>
            <button mat-button type="button" (click)="cancel()">Cancel</button>
          </div>
        </div>
      } @else {
        <div class="or" aria-hidden="true"><span>or</span></div>
        <div #button class="gbtn"></div>
        @if (busy()) {
          <p class="bab-muted small">Signing in with Google...</p>
        }
      }
      @if (error()) {
        <p class="bab-form-error" role="alert">{{ error() }}</p>
      }
    }
  `,
  styles: `
    :host {
      display: block;
    }
    .or {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 16px 0 12px;
      color: var(--mat-sys-on-surface-variant);
      font: var(--mat-sys-label-medium);
    }
    .or::before,
    .or::after {
      content: '';
      flex: 1;
      height: 1px;
      background: var(--mat-sys-outline-variant);
    }
    .gbtn {
      display: flex;
      justify-content: center;
      min-height: 44px;
    }
    .consent {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-top: 16px;
      padding: 14px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.7);
    }
    .consent p {
      margin: 0 0 4px;
    }
    .actions {
      display: flex;
      gap: 8px;
      margin-top: 8px;
    }
    .small {
      font: var(--mat-sys-body-small);
      text-align: center;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GoogleSignInComponent implements OnDestroy {
  private readonly api = inject(AuthApi);
  private readonly auth = inject(AuthService);
  private readonly zone = inject(NgZone);

  /** Emitted after a successful Google sign-in or sign-up. */
  readonly signedIn = output<UserOut>();

  private readonly buttonEl = viewChild<ElementRef<HTMLElement>>('button');
  protected readonly enabled = signal(false);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly pendingCredential = signal<string | null>(null);
  protected readonly pendingEmail = signal<string | null>(null);
  protected readonly adult = signal(false);
  protected readonly privacy = signal(false);
  private destroyed = false;

  constructor() {
    this.api.googleConfig().subscribe({
      next: (c) => {
        if (c.enabled && c.client_id) {
          this.enabled.set(true);
          void this.setUp(c.client_id);
        }
      },
      error: () => undefined, // No Google button; email sign-in still works.
    });
  }

  private async setUp(clientId: string): Promise<void> {
    try {
      await loadGis();
    } catch {
      this.error.set('Could not load Google sign-in. Use your email and password.');
      return;
    }
    if (this.destroyed || !window.google) return;
    window.google.accounts.id.initialize({
      client_id: clientId,
      ux_mode: 'popup',
      itp_support: true,
      callback: (r) => this.zone.run(() => this.onCredential(r.credential)),
    });
    this.render();
  }

  private render(): void {
    const el = this.buttonEl()?.nativeElement;
    if (!el || !window.google) return;
    window.google.accounts.id.renderButton(el, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      shape: 'pill',
      text: 'continue_with',
      logo_alignment: 'left',
      width: Math.min(360, el.clientWidth || 320),
    });
  }

  private onCredential(credential: string): void {
    this.pendingCredential.set(credential);
    this.send(false);
  }

  protected send(withConsent: boolean): void {
    const credential = this.pendingCredential();
    if (!credential) return;
    this.busy.set(true);
    this.error.set(null);
    this.auth
      .googleSignIn({
        credential,
        ...(withConsent ? { is_adult: this.adult(), accepts_privacy: this.privacy() } : {}),
      })
      .subscribe({
        next: (user) => {
          this.busy.set(false);
          this.pendingCredential.set(null);
          this.signedIn.emit(user);
        },
        error: (err: unknown) => {
          this.busy.set(false);
          if (apiErrorCode(err) === 'consent_required') {
            this.pendingEmail.set(emailFromToken(credential));
            return; // The consent panel is showing; the user confirms and resends.
          }
          this.cancel();
          this.error.set(apiErrorMessage(err));
        },
      });
  }

  protected cancel(): void {
    this.pendingCredential.set(null);
    this.pendingEmail.set(null);
    this.adult.set(false);
    this.privacy.set(false);
    // The button element is re-created; draw it again.
    queueMicrotask(() => setTimeout(() => this.render()));
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    window.google?.accounts.id.cancel();
  }
}

import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

/** Empty state for sections whose milestone has not been built yet. */
@Component({
  selector: 'app-upcoming-page',
  imports: [MatIconModule],
  template: `
    <section class="bab-page">
      <h1 class="bab-page-title">{{ title() }}</h1>
      <div class="empty">
        <mat-icon>{{ icon() }}</mat-icon>
        <p>{{ blurb() }}</p>
        <p class="bab-muted">Not available yet in this build.</p>
      </div>
    </section>
  `,
  styles: `
    .empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding: 48px 16px;
      border-radius: 16px;
      background: var(--mat-sys-surface-container-low);
    }
    mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: var(--mat-sys-primary);
    }
    p {
      margin: 12px 0 0;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UpcomingPageComponent {
  readonly title = input.required<string>();
  readonly icon = input('construction');
  readonly blurb = input('');
}

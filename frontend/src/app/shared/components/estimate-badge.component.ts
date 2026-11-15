import { ChangeDetectionStrategy, Component } from '@angular/core';

/** Small "estimate" label shown beside estimated numbers. */
@Component({
  selector: 'app-estimate',
  template: 'estimate',
  styles: `
    :host {
      display: inline-block;
      margin-left: 6px;
      padding: 0 6px;
      border-radius: 8px;
      font: var(--mat-sys-label-small);
      color: var(--mat-sys-on-tertiary-container);
      background: var(--mat-sys-tertiary-container);
      vertical-align: middle;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EstimateBadgeComponent {}

import { ChangeDetectionStrategy, Component } from '@angular/core';

import { MoreTilesComponent } from '../../core/layout/more-tiles.component';

@Component({
  selector: 'app-more-page',
  imports: [MoreTilesComponent],
  template: `
    <section class="bab-page">
      <h1 class="bab-page-title">More</h1>
      <app-more-tiles />
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MorePage {}

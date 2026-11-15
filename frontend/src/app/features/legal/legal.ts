import { inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';

import { AccountApi } from '../../core/api/account.api';

/** App name and contact email from the server configuration. */
export function publicConfigResource() {
  const api = inject(AccountApi);
  return rxResource({ stream: () => api.publicConfig() });
}

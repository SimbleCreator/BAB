/** Types matching the backend OpenAPI schema (`/openapi.json`). */

export interface HealthOut {
  status: 'ok';
  version: string;
}

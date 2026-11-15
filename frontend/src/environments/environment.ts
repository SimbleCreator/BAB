// Production build. The API base URL is set at build time, for example:
//   npx ng build --define "BAB_API_URL='https://api.example.com/api/v1'"
// Without it the app calls /api/v1 on its own origin (when the static host proxies /api).
// See docs/deploy.md.
declare const BAB_API_URL: string | undefined;

export const environment = {
  production: true,
  apiBaseUrl: typeof BAB_API_URL === 'string' && BAB_API_URL ? BAB_API_URL : '/api/v1',
};

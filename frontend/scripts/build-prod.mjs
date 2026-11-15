// Production build that reads the API URL from the BAB_API_URL environment variable.
// Usage: BAB_API_URL=https://api.example.com/api/v1 npm run build:prod
import { spawnSync } from 'node:child_process';

const api = process.env.BAB_API_URL ?? '';
if (api && !/^https:\/\/[^'"\s]+$/.test(api)) {
  console.error('BAB_API_URL must be an https:// URL without quotes or spaces.');
  process.exit(1);
}
const args = ['ng', 'build', '--configuration', 'production'];
if (api) args.push('--define', `BAB_API_URL='${api}'`);
console.log(api ? `API: ${api}` : 'API: same origin (/api/v1)');
const r = spawnSync('npx', args, { stdio: 'inherit', shell: process.platform === 'win32' });
process.exit(r.status ?? 1);

// Cloudflare Pages Function: forwards every /api/* request to the B.A.B API.
//
// Why: the browser then sees the app and the API on one site, so the httpOnly refresh
// cookie works in every browser (no third-party cookies). Set API_ORIGIN in the Pages
// project's environment variables, for example https://bab-api.onrender.com
//
// Only /api/* runs this code; all other paths are plain static files.

const HOP_BY_HOP = ['connection', 'keep-alive', 'transfer-encoding', 'upgrade', 'host'];

export async function onRequest({ request, env }) {
  const origin = (env.API_ORIGIN || '').replace(/\/+$/, '');
  if (!/^https:\/\/[^/]+$/.test(origin)) {
    return Response.json(
      { detail: 'The API address is not configured.', code: 'proxy_not_configured' },
      { status: 503 },
    );
  }

  const url = new URL(request.url);
  const target = origin + url.pathname + url.search;

  const headers = new Headers(request.headers);
  for (const h of HOP_BY_HOP) headers.delete(h);
  // The API's rate limiter needs the visitor's address, not Cloudflare's.
  const client = request.headers.get('CF-Connecting-IP');
  if (client) headers.set('X-Forwarded-For', client);
  headers.set('X-Forwarded-Proto', 'https');

  const hasBody = !['GET', 'HEAD'].includes(request.method);
  let upstream;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? request.body : undefined,
      redirect: 'manual',
    });
  } catch {
    return Response.json(
      { detail: 'Cannot reach the server. Try again in a minute.', code: 'api_unreachable' },
      { status: 502 },
    );
  }

  // Pass the response through as is (status, body, Set-Cookie and all other headers).
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: upstream.headers,
  });
}

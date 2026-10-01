import { DurableObject } from 'cloudflare:workers';
import { GitHub } from './github.js';
import { Engine } from './engine.js';
import { dashboard } from './dashboard.js';

export class FetchScheduler extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.engine = new Engine(ctx.storage, new GitHub(env));
    this.queue = Promise.resolve();
  }

  async fetch(request) {
    const path = new URL(request.url).pathname;
    if (path === '/status') return Response.json(await this.engine.status());
    // Serialize ticks across network waits. Persisted intent handles eviction.
    const operation = this.queue.then(() => this.engine.tick({ test: path === '/test' }));
    this.queue = operation.catch(() => {});
    const state = await operation;
    return Response.json({ accepted: true, slot: state.records.at(-1)?.slot, error: state.error });
  }
}

function instance(env) {
  return env.SCHEDULER.get(env.SCHEDULER.idFromName('techjobs-africa'));
}

async function authorized(request, env) {
  const token = request.headers.get('Authorization');
  if (!token || !env.SCHEDULER_GITHUB_TOKEN) return false;
  const encoder = new TextEncoder();
  const [supplied, expected] = await Promise.all([
    crypto.subtle.digest('SHA-256', encoder.encode(token)),
    crypto.subtle.digest('SHA-256', encoder.encode(`Bearer ${env.SCHEDULER_GITHUB_TOKEN}`)),
  ]);
  const a = new Uint8Array(supplied), b = new Uint8Array(expected);
  let difference = 0;
  for (let i = 0; i < a.length; i++) difference |= a[i] ^ b[i];
  return difference === 0;
}

export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(instance(env).fetch(new Request('https://scheduler.internal/tick', { method: 'POST' })));
  },
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (request.method === 'GET' && path === '/') {
      return new Response(dashboard, { headers: {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff',
        'Content-Security-Policy': "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
      } });
    }
    if (request.method === 'GET' && ['/status', '/health'].includes(path)) {
      const response = await instance(env).fetch(new Request('https://scheduler.internal/status'));
      const status = await response.json();
      return Response.json(status, {
        status: path === '/health' && !status.healthy ? 503 : 200,
        headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
      });
    }
    if (request.method === 'POST' && path === '/test') {
      if (!await authorized(request, env)) return new Response('Unauthorized', { status: 401 });
      return instance(env).fetch(new Request('https://scheduler.internal/test', { method: 'POST' }));
    }
    return new Response('Not found', { status: 404 });
  },
};

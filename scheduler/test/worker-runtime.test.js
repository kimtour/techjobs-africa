import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Miniflare, convertV4MiniflareOptions } from 'miniflare';

// Run the compiled Worker in Cloudflare's local runtime, including its SQLite
// Durable Object. No live GitHub calls or real credentials are used.
test('Worker serves status and dashboard while protecting every dispatch route', async () => {
  const output = mkdtempSync(join(tmpdir(), 'techjobs-scheduler-'));
  const dispatches = [];
  let mf;
  try {
    execFileSync(process.execPath, ['node_modules/wrangler/bin/wrangler.js', 'deploy', '--dry-run', '--outdir', output], {
      env: { ...process.env, WRANGLER_LOG_PATH: join(output, 'logs'), WRANGLER_SEND_METRICS: 'false' },
      stdio: 'pipe',
    });
    mf = new Miniflare(convertV4MiniflareOptions({
      modules: true,
      modulesRoot: output,
      scriptPath: join(output, 'worker.js'),
      compatibilityDate: '2026-07-30',
      bindings: {
        GITHUB_REPOSITORY: 'kimtour/techjobs-africa',
        GITHUB_WORKFLOW: 'ingest-and-build.yml', GITHUB_REF: 'main',
        SCHEDULER_GITHUB_TOKEN: 'local-test-token',
      },
      durableObjects: { SCHEDULER: { className: 'FetchScheduler', useSQLite: true } },
      outboundService: async request => {
        const url = new URL(request.url);
        assert.equal(url.origin, 'https://api.github.com');
        assert.equal(request.headers.get('Authorization'), 'Bearer local-test-token');
        if (request.method === 'GET') return Response.json({ workflow_runs: [] });
        dispatches.push(await request.json());
        return new Response(null, { status: 204 });
      },
    }));
    const statusResponse = await mf.dispatchFetch('https://scheduler.test/status');
    assert.equal(statusResponse.status, 200);
    const status = await statusResponse.json();
    assert.equal(status.timezone, 'Africa/Nairobi');
    assert.equal(status.healthy, false);
    assert.deepEqual(status.records, []);
    assert.equal(JSON.stringify(status).includes('local-test-token'), false);
    const dashboard = await mf.dispatchFetch('https://scheduler.test/');
    assert.equal(dashboard.status, 200);
    assert.match(dashboard.headers.get('Content-Type'), /text\/html/);
    assert.match(await dashboard.text(), /TechJobs Africa · Fetch status/);
    assert.equal((await mf.dispatchFetch('https://scheduler.test/health')).status, 503);
    assert.equal((await mf.dispatchFetch('https://scheduler.test/test', { method: 'POST' })).status, 401);
    assert.equal((await mf.dispatchFetch('https://scheduler.test/test', {
      method: 'POST', headers: { Authorization: 'Bearer incorrect' },
    })).status, 401);
    assert.equal((await mf.dispatchFetch('https://scheduler.test/tick', { method: 'POST' })).status, 404);
    assert.equal((await mf.dispatchFetch('https://scheduler.test/test')).status, 404);
    const accepted = await mf.dispatchFetch('https://scheduler.test/test', {
      method: 'POST', headers: { Authorization: 'Bearer local-test-token' },
    });
    const triggered = await accepted.json();
    assert.equal(triggered.error, null);
    assert.match(triggered.slot, /^test-/);
    assert.ok(dispatches.some(body => body.ref === 'main' && body.inputs.scheduler_slot === triggered.slot));
  } finally {
    if (mf) await mf.dispose();
    rmSync(output, { recursive: true, force: true });
  }
});

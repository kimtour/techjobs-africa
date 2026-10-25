import test from 'node:test';
import assert from 'node:assert/strict';
import { Engine } from '../src/engine.js';
import { GitHub } from '../src/github.js';
import { latestSlot, nextSlot, shouldDispatch, runTitle, MINUTE } from '../src/policy.js';

const DUE = Date.parse('2026-10-01T12:00:00.000Z');
const SLOT = new Date(DUE).toISOString();

function fixture(start = DUE) {
  let now = start;
  let stored;
  const calls = [];
  const github = {
    listedRuns: [],
    listedJobs: [],
    async runs() { return { workflow_runs: structuredClone(this.listedRuns) }; },
    async claim() { return null; },
    async jobs() { return { jobs: structuredClone(this.listedJobs) }; },
    async dispatch(slot) { calls.push(['dispatch', slot]); },
    async alert(slot, kind) { calls.push(['alert', slot, kind]); },
    async request() { return { workflow_runs: [] }; },
  };
  const storage = {
    async get() { return structuredClone(stored); },
    async put(key, value) { stored = structuredClone(value); },
  };
  const engine = new Engine(storage, github, () => now);
  return {
    engine, github, storage, calls,
    advance(minutes) { now += minutes * MINUTE; },
    state() { return structuredClone(stored); },
  };
}

function run(status = 'in_progress', conclusion = null) {
  return {
    id: 123, display_title: runTitle(SLOT), status, conclusion,
    html_url: 'https://github.com/kimtour/techjobs-africa/actions/runs/123',
    created_at: new Date(DUE + MINUTE).toISOString(),
    updated_at: new Date(DUE + 8 * MINUTE).toISOString(),
  };
}

test('all five requested EAT slots and overnight rollover are preserved', () => {
  const slots = [];
  let now = Date.parse('2026-10-01T00:00:00+03:00');
  for (let i = 0; i < 5; i++) {
    now = nextSlot(now);
    const eat = new Date(now + 3 * 3_600_000);
    slots.push([eat.getUTCHours(), eat.getUTCMinutes()]);
    assert.equal(latestSlot(now), now);
  }
  assert.deepEqual(slots, [6, 9, 12, 15, 19].map(hour => [hour, 0]));
  assert.equal(new Date(nextSlot(now)).toISOString(), '2026-10-02T03:00:00.000Z');
});

test('late cron tick catches up without dispatching the same slot every minute', async () => {
  const f = fixture(DUE + 2 * MINUTE);
  await f.engine.tick();
  f.advance(1);
  await f.engine.tick();
  assert.deepEqual(f.calls, [['dispatch', SLOT]]);
  assert.equal(f.state().records.length, 1);
});

test('accepted request with lost response is reconciled before any retry', async () => {
  const f = fixture();
  f.github.dispatch = async slot => {
    f.calls.push(['dispatch', slot]);
    assert.equal(f.state().records[0].attempts, 1, 'intent is durable before network call');
    throw new Error('response lost');
  };
  await f.engine.tick();
  // Simulate eviction: recreate the engine with the same persisted storage.
  f.advance(4);
  f.github.listedRuns = [run()];
  const restarted = new Engine(f.storage, f.github, () => DUE + 4 * MINUTE);
  await restarted.tick();
  assert.equal(f.calls.length, 1);
  assert.equal(f.state().records[0].run_id, 123);
});

test('dispatch errors retry at three-minute intervals with three attempts maximum', async () => {
  const f = fixture();
  f.github.dispatch = async slot => { f.calls.push(['dispatch', slot]); throw new Error('timeout'); };
  for (let i = 0; i < 10; i++) { await f.engine.tick(); f.advance(1); }
  assert.equal(f.calls.filter(([type]) => type === 'dispatch').length, 3);
  assert.equal(f.state().records[0].error, 'github_request_failed');
});

test('API outage does not dispatch blindly or leak exception details', async () => {
  const f = fixture();
  f.github.runs = async () => { throw new Error('Authorization: secret-value'); };
  await f.engine.tick();
  assert.equal(f.calls.length, 0);
  assert.equal(f.state().error, 'github_request_failed');
  assert.equal(JSON.stringify(f.state()).includes('secret-value'), false);
});

test('queued workflow is not counted as an actual fetch start and alerts once', async () => {
  const f = fixture();
  await f.engine.tick();
  f.github.listedRuns = [run('queued')];
  f.advance(10);
  await f.engine.tick();
  f.advance(1);
  await f.engine.tick();
  assert.deepEqual(f.calls.filter(([type]) => type === 'alert'), [['alert', SLOT, 'fetch_not_started']]);
  assert.equal(f.state().records[0].fetch_started_at, undefined);
});

test('actual ingestion start and successful completion are tracked', async () => {
  const f = fixture();
  await f.engine.tick();
  f.github.listedRuns = [run('completed', 'success')];
  f.github.listedJobs = [{ steps: [{
    name: 'Ingest approved sources', status: 'completed', conclusion: 'success',
    started_at: new Date(DUE + 2 * MINUTE).toISOString(),
  }] }];
  f.advance(8);
  await f.engine.tick();
  assert.equal(f.state().records[0].fetch_started_at, DUE + 2 * MINUTE);
  assert.equal(f.state().records[0].conclusion, 'success');
  assert.equal(f.calls.filter(([type]) => type === 'alert').length, 0);
});

test('failed fetch produces a distinct workflow failure alert', async () => {
  const f = fixture();
  await f.engine.tick();
  f.github.listedRuns = [run('completed', 'failure')];
  f.advance(8);
  await f.engine.tick();
  assert.deepEqual(f.calls.filter(([type]) => type === 'alert'), [['alert', SLOT, 'workflow_failed']]);
});

test('skipped duplicate ingestion step cannot be mistaken for a fetch', async () => {
  const f = fixture();
  await f.engine.tick();
  f.github.listedRuns = [run('completed', 'success')];
  f.github.listedJobs = [{ steps: [{
    name: 'Ingest approved sources', status: 'completed', conclusion: 'skipped',
    started_at: new Date(DUE + MINUTE).toISOString(),
  }] }];
  f.advance(10);
  await f.engine.tick();
  assert.equal(f.state().records[0].fetch_started_at, undefined);
  assert.equal(f.calls.at(-1)[2], 'fetch_not_started');
});

test('long-running workflow alerts at forty minutes', async () => {
  const f = fixture();
  await f.engine.tick();
  f.github.listedRuns = [run()];
  f.github.listedJobs = [{ steps: [{
    name: 'Ingest approved sources', status: 'in_progress',
    started_at: new Date(DUE + MINUTE).toISOString(),
  }] }];
  f.advance(40);
  await f.engine.tick();
  assert.equal(f.calls.at(-1)[2], 'completion_overdue');
});

test('scheduler outage records missed slots without replaying old fetches', async () => {
  const f = fixture();
  await f.engine.tick();
  f.advance(5 * 60);
  await f.engine.tick();
  const missed = f.state().records.filter(record => record.status === 'missed');
  assert.ok(missed.some(record => record.slot === '2026-10-01T16:00:00.000Z'));
  assert.deepEqual(missed.map(record => record.slot), [SLOT, '2026-10-01T16:00:00.000Z']);
  assert.equal(f.calls.filter(([type]) => type === 'dispatch').length, 1);
});

test('startup does not replay an old slot; authenticated tests can fetch between slots', async () => {
  const f = fixture(DUE + 45 * MINUTE);
  await f.engine.tick();
  assert.equal(f.calls.length, 0);
  await f.engine.tick({ test: true });
  assert.equal(f.calls.length, 1);
  assert.equal(f.calls[0][1], 'test-2026-10-01T12:45:00.000Z');
});

test('health reports stale watchdog and next slot', async () => {
  const f = fixture();
  assert.equal((await f.engine.status()).healthy, false);
  await f.engine.tick();
  assert.equal((await f.engine.status()).healthy, true);
  assert.deepEqual((await f.engine.status()).scheduled_times_eat, ['06:00', '09:00', '12:00', '15:00', '19:00']);
  f.advance(6);
  assert.equal((await f.engine.status()).healthy, false);
  assert.equal((await f.engine.status()).next_fetch_at, '2026-10-01T16:00:00.000Z');
});

test('dispatch policy never retries past the catch-up window or after identifying a run', () => {
  const record = { due_at: DUE, attempts: 1, last_attempt_at: DUE };
  assert.equal(shouldDispatch(record, DUE + 31 * MINUTE), false);
  assert.equal(shouldDispatch({ ...record, run_id: 123 }, DUE + 5 * MINUTE), false);
});

test('GitHub request restricts repository and ref, encodes inputs, and redacts HTTP errors', async () => {
  const env = {
    GITHUB_REPOSITORY: 'kimtour/techjobs-africa', GITHUB_WORKFLOW: 'ingest-and-build.yml',
    GITHUB_REF: 'main', SCHEDULER_GITHUB_TOKEN: 'test-secret',
  };
  const client = new GitHub(env, async function (url, options) {
    assert.equal(this, undefined);
    assert.equal(url, 'https://api.github.com/repos/kimtour/techjobs-africa/actions/workflows/ingest-and-build.yml/dispatches');
    assert.deepEqual(JSON.parse(options.body), { ref: 'main', inputs: { scheduler_slot: SLOT } });
    assert.equal(options.headers.Authorization, 'Bearer test-secret');
    return new Response(null, { status: 204 });
  });
  await client.dispatch(SLOT);
  const denied = new GitHub(env, async () => new Response('private body', { status: 403 }));
  await assert.rejects(denied.dispatch(SLOT), /^Error: github_http_403$/);
});


test('duplicate dispatches follow actual fetch steps without reading private claims', async () => {
  const f = fixture();
  await f.engine.tick();
  f.github.listedRuns = [run('completed', 'cancelled'), { ...run(), id: 456 }];
  f.github.claim = async () => { throw new Error('Private claims must not be requested'); };
  f.github.listedJobs = [{ steps: [{
    name: 'Ingest approved sources', status: 'in_progress',
    started_at: new Date(DUE + 4 * MINUTE).toISOString(),
  }] }];
  f.github.jobs = async id => ({ jobs: id === 456 ? f.github.listedJobs : [] });
  f.advance(5);
  await f.engine.tick();
  assert.equal(f.state().records[0].run_id, 456);
  assert.equal(f.state().records[0].fetch_started_at, DUE + 4 * MINUTE);
  assert.equal(f.calls.filter(([type]) => type === 'alert').length, 0);
});

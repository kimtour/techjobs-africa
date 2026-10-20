import {
  latestSlot, nextSlot, slotName, runTitle, alertTitle, shouldDispatch, alertKinds,
  CATCHUP_WINDOW, MINUTE,
} from './policy.js';

const HISTORY_LIMIT = 90;

function safeError(error) {
  return /^github_http_\d{3}$/.test(error?.message) ? error.message : 'github_request_failed';
}

export class Engine {
  constructor(storage, github, clock = Date.now) {
    this.storage = storage;
    this.github = github;
    this.clock = clock;
  }

  async save(state) {
    state.records = state.records.slice(-HISTORY_LIMIT);
    await this.storage.put('state', state);
  }

  async tick({ test = false } = {}) {
    const now = this.clock();
    const state = await this.storage.get('state') || { records: [], activated_at: now };
    const previousTick = state.last_tick_at;
    state.last_tick_at = now;
    // Detect an outage across scheduled slots; record missed slots, don't replay
    // hours of old ingestion. Startup only considers the current catch-up window.
    const since = previousTick ?? now - CATCHUP_WINDOW;
    const due = [];
    for (let slot = latestSlot(now); slot > since; slot = latestSlot(slot - 1)) {
      due.unshift(slot);
      if (due.length >= HISTORY_LIMIT) break;
    }
    if (test) due.push(now);
    for (const timestamp of due) {
      const slot = slotName(timestamp, test && timestamp === now);
      if (!state.records.some(record => record.slot === slot)) {
        state.records.push({ slot, due_at: timestamp, attempts: 0, alerts: {}, test: slot.startsWith('test-') });
      }
    }
    await this.save(state);
    const outstanding = state.records.filter(record => !record.completed_at ||
      (!record.fetch_started_at && now - record.due_at < 60 * MINUTE) ||
      alertKinds(record, now).some(kind => record.alerts[kind]?.state !== 'sent'));
    if (!outstanding.length) {
      state.last_check_at = now;
      state.error = null;
      await this.save(state);
      return state;
    }
    let runs;
    try {
      runs = (await this.github.runs()).workflow_runs;
    } catch (error) {
      state.error = safeError(error);
      console.error(JSON.stringify({ event: 'github_check_failed', error: state.error }));
      await this.save(state);
      return state;
    }
    state.last_check_at = now;
    state.error = null;
    for (const record of outstanding) {
      try {
        const matches = runs.filter(run => run.display_title === runTitle(record.slot));
        // With duplicate accepted dispatches, the data-branch claim identifies
        // the actual fetch owner; an earlier cancelled/skipped run isn't it.
        const claim = matches.length > 1 ? await this.github.claim(record.slot) : null;
        const run = matches.find(run => String(run.id) === claim?.run_id) ||
          matches.find(run => run.status !== 'completed') ||
          matches.sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at))[0];
        if (run) {
          if (record.run_id !== run.id) {
            delete record.completed_at;
            delete record.conclusion;
            delete record.fetch_started_at;
            delete record.workflow_started_at;
          }
          record.run_id = run.id;
          record.run_url = run.html_url;
          record.run_created_at = Date.parse(run.created_at);
          record.status = run.status;
          // run_started_at is also populated for queued runs, so gate it on
          // execution status. Preserve this evidence across delayed API reads.
          if (['in_progress', 'completed'].includes(run.status)) {
            const startedAt = Date.parse(run.run_started_at);
            if (Number.isFinite(startedAt) && startedAt <= now) {
              record.workflow_started_at ||= startedAt;
            }
          }
          if (!record.fetch_started_at) {
            const jobs = (await this.github.jobs(run.id)).jobs;
            const fetchStep = jobs.flatMap(job => job.steps || [])
              .find(step => step.name === 'Ingest approved sources' && step.started_at &&
                ['in_progress', 'completed'].includes(step.status) && step.conclusion !== 'skipped' &&
                Number.isFinite(Date.parse(step.started_at)) && Date.parse(step.started_at) <= now);
            if (fetchStep) record.fetch_started_at = Date.parse(fetchStep.started_at);
          }
          if (run.status === 'completed') {
            record.completed_at = Date.parse(run.updated_at);
            record.conclusion = run.conclusion;
          }
          record.error = null;
        } else if (shouldDispatch(record, now)) {
          // Persist BEFORE sending. After a timeout/restart, reconcile GitHub
          // first and wait three minutes before retrying an ambiguous request.
          record.attempts += 1;
          record.last_attempt_at = now;
          record.status = 'dispatching';
          await this.save(state);
          await this.github.dispatch(record.slot);
          record.status = 'awaiting_run';
          record.dispatch_accepted_at = now;
          record.error = null;
          console.log(JSON.stringify({ event: 'fetch_dispatched', slot: record.slot, attempt: record.attempts }));
        }
      } catch (error) {
        record.error = safeError(error);
        record.status ||= 'dispatch_failed';
        // An unavailable observation is not evidence of a missing workflow.
        // Keep the error visible in /health and retry on the next watchdog tick.
        await this.save(state);
        continue;
      }
      // Don't indefinitely poll old runs/alerts. All abandoned slots remain in
      // the public ledger; failures and deadlines are still recorded below.
      for (const kind of alertKinds(record, now)) {
        const alert = record.alerts[kind] ||= { state: 'pending', detected_at: now, attempts: 0 };
        if (alert.state === 'sent') continue;
        if (alert.last_attempt_at && now - alert.last_attempt_at < 5 * MINUTE) continue;
        try {
          // Alert requests are idempotent on GitHub run title after ambiguous acceptance.
          const alertRuns = (await this.github.request('/actions/workflows/scheduler-alert.yml/runs?per_page=100')).workflow_runs;
          const existing = alertRuns.find(run => run.display_title === alertTitle(record.slot, kind));
          if (existing) {
            alert.state = 'sent';
            alert.run_url = existing.html_url;
            continue;
          }
          alert.attempts += 1;
          alert.last_attempt_at = now;
          await this.save(state);
          await this.github.alert(record.slot, kind);
          alert.state = 'sent';
          alert.sent_at = now;
          console.error(JSON.stringify({ event: kind, slot: record.slot, run_url: record.run_url || null }));
        } catch (error) {
          alert.error = safeError(error);
        }
      }
      if (!record.run_id && now - record.due_at > CATCHUP_WINDOW) {
        record.status = 'missed';
        record.completed_at = now;
        record.conclusion = 'missed';
      }
      await this.save(state);
    }
    return state;
  }

  async status() {
    const now = this.clock();
    const state = await this.storage.get('state');
    const last = state?.records.at(-1);
    const healthy = Boolean(state?.last_tick_at && now - state.last_tick_at < 5 * MINUTE &&
      !state.error && !last?.error && !Object.keys(last?.alerts || {}).length);
    return {
      healthy,
      timezone: 'Africa/Nairobi',
      scheduled_times_eat: ['01:00', '07:00', '09:00', '11:00', '13:00', '15:00', '17:00', '19:00', '21:00'],
      next_fetch_at: new Date(nextSlot(now)).toISOString(),
      checked_at: new Date(now).toISOString(),
      ...(state || { records: [] }),
    };
  }
}


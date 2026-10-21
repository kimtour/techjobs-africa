// 06:00, 09:00, 12:00, 15:00 and 19:00 Africa/Nairobi (UTC+3).
export const UTC_HOURS = [3, 6, 9, 12, 16];
export const EAT_TIMES = UTC_HOURS.map(hour => `${String((hour + 3) % 24).padStart(2, '0')}:00`);
export const MINUTE = 60_000;
export const START_DEADLINE = 10 * MINUTE;
export const RETRY_INTERVAL = 3 * MINUTE;
export const CATCHUP_WINDOW = 30 * MINUTE;
export const COMPLETION_DEADLINE = 40 * MINUTE;
export const MAX_ATTEMPTS = 3;

export function latestSlot(now) {
  const day = new Date(now);
  day.setUTCHours(0, 0, 0, 0);
  const slots = [-1, 0].flatMap(offset => UTC_HOURS.map(hour =>
    day.getTime() + offset * 86_400_000 + hour * 3_600_000));
  return Math.max(...slots.filter(slot => slot <= now));
}

export function nextSlot(now) {
  const day = new Date(now);
  day.setUTCHours(0, 0, 0, 0);
  const slots = [0, 1].flatMap(offset => UTC_HOURS.map(hour =>
    day.getTime() + offset * 86_400_000 + hour * 3_600_000));
  return Math.min(...slots.filter(slot => slot > now));
}

export function slotName(timestamp, test = false) {
  return `${test ? 'test-' : ''}${new Date(timestamp).toISOString()}`;
}

export function runTitle(slot) {
  return `Job fetch · ${slot}`;
}

export function alertTitle(slot, kind) {
  return `Scheduler alert · ${slot} · ${kind}`;
}

export function shouldDispatch(record, now) {
  return !record.run_id && record.attempts < MAX_ATTEMPTS &&
    now - record.due_at <= CATCHUP_WINDOW &&
    (!record.last_attempt_at || now - record.last_attempt_at >= RETRY_INTERVAL);
}

export function alertKinds(record, now) {
  const kinds = [];
  if (!record.fetch_started_at && now - record.due_at >= START_DEADLINE) {
    kinds.push('fetch_not_started');
  }
  if (!record.completed_at && now - record.due_at >= COMPLETION_DEADLINE) {
    kinds.push('completion_overdue');
  }
  if (record.completed_at && !['success', 'skipped'].includes(record.conclusion)) {
    kinds.push('workflow_failed');
  }
  return kinds;
}

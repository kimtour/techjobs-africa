// Exercise the already deployed Worker; keep the credential in memory only.
import { appendFileSync } from 'node:fs';

const url = 'https://techjobs-africa-scheduler.kimani-mutua.workers.dev';
if (!process.env.SCHEDULER_GITHUB_TOKEN) throw new Error('Scheduler verification credential is missing');
const response = await fetch(`${url}/test`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${process.env.SCHEDULER_GITHUB_TOKEN}` },
  signal: AbortSignal.timeout(30000),
});
if (!response.ok) throw new Error(`Worker test request failed: HTTP ${response.status}`);
const test = await response.json();
if (test.error || !test.slot?.startsWith('test-')) throw new Error('Worker did not accept a test slot');
console.log(`Worker accepted verification slot: ${test.slot}`);
for (let attempt = 0; attempt < 28; attempt++) {
  await new Promise(resolve => setTimeout(resolve, 30000));
  const statusResponse = await fetch(`${url}/status`, { signal: AbortSignal.timeout(15000) });
  if (!statusResponse.ok) throw new Error(`Worker status failed: HTTP ${statusResponse.status}`);
  const status = await statusResponse.json();
  const record = status.records.find(item => item.slot === test.slot);
  if (record?.conclusion && record.conclusion !== 'success') throw new Error('Worker-triggered ingestion failed');
  if (record?.conclusion === 'success' && record.fetch_started_at && record.completed_at) {
    appendFileSync(process.env.GITHUB_STEP_SUMMARY,
      `Worker-triggered source ingestion started and completed successfully.\n\n[Fetch run](${record.run_url}) · [Scheduler status](${url}/)\n`);
    console.log(`Verified successful source fetch: ${record.run_url}`);
    process.exit(0);
  }
}
throw new Error('Worker verification fetch did not complete within fourteen minutes');

import { appendFileSync } from 'node:fs';

const headers = {
  Authorization: `Bearer ${process.env.CLOUDFLARE_API_TOKEN}`,
  'Content-Type': 'application/json',
};
const result = await fetch(
  `https://api.cloudflare.com/client/v4/accounts/${process.env.CLOUDFLARE_ACCOUNT_ID}/workers/subdomain`,
  { headers, signal: AbortSignal.timeout(15000) },
);
if (!result.ok) throw new Error(`Cannot identify worker address: HTTP ${result.status}`);
const payload = await result.json();
if (!payload.success || !payload.result?.subdomain) throw new Error('Workers subdomain is not configured');
const url = `https://techjobs-africa-scheduler.${payload.result.subdomain}.workers.dev`;
let status;
for (let attempt = 0; attempt < 6; attempt++) {
  try {
    const response = await fetch(`${url}/status`, { signal: AbortSignal.timeout(10000) });
    if (response.ok) { status = await response.json(); break; }
  } catch { /* Allow a brief deployment propagation delay. */ }
  await new Promise(resolve => setTimeout(resolve, 5000));
}
if (!status || status.timezone !== 'Africa/Nairobi') throw new Error('Scheduler status endpoint did not respond');
appendFileSync(process.env.GITHUB_STEP_SUMMARY,
  `## Cloudflare fetch scheduler\n\n[Live status](${url}) · [Status JSON](${url}/status) · [Health check](${url}/health)\n\n`);
console.log(`Scheduler URL: ${url}`);
if (process.env.TEST_FETCH === 'true') {
  const response = await fetch(`${url}/test`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${process.env.SCHEDULER_GITHUB_TOKEN}` },
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) throw new Error(`Test trigger failed: HTTP ${response.status}`);
  const test = await response.json();
  if (test.error || !test.slot?.startsWith('test-')) throw new Error('Scheduler could not dispatch the test fetch');
  appendFileSync(process.env.GITHUB_STEP_SUMMARY, `Test fetch slot: \`${test.slot}\`. Check the live status for its actual start and completion.\n`);
  console.log(`Test fetch slot: ${test.slot}`);
}

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

const document = new JSDOM(readFileSync(new URL('../dist/index.html', import.meta.url), 'utf8')).window.document;
const payload = JSON.parse(readFileSync(new URL('../src/data/jobs.json', import.meta.url), 'utf8'));
const retired = source => source === 'bebee' || source.startsWith('employer_');
const expected = payload.jobs.filter(job => job.status === 'ACTIVE'
  && job.eligibility_level !== 'RESTRICTED'
  && !retired(job.job_id.split(':')[0])
  && job.sources.some(source => !retired(source)));
const allCards = [...document.querySelectorAll('[data-source="all"] [data-job-id]')];
assert.deepEqual(allCards.map(card => card.dataset.jobId).sort(), expected.map(job => job.job_id).sort());
assert.equal(document.querySelector('[data-source="company_careers"]'), null);
assert.equal(document.querySelector('#direct-filter, #employer-filter, #sector-filter'), null);
assert.equal(document.querySelector('[data-employer], [data-direct], [data-sectors]'), null);
const panels = [...document.querySelectorAll('[data-source-group]')]
  .sort((a, b) => Number(a.style.order) - Number(b.style.order));
if (expected.length) assert.equal(panels[0].dataset.source, 'all');
for (const panel of panels) {
  assert(!retired(panel.dataset.source));
  assert(panel.querySelector('h3'));
  assert(panel.querySelector('[data-period="latest"]'));
  assert.equal(panel.querySelector('[data-source-feed] h3'), null);
  assert.equal(panel.querySelector('[data-source-feed] [data-period]'), null);
}
console.log(`Verified ${panels.length} source panels and ${allCards.length} accepted jobs; retired company feed and filters are absent.`);

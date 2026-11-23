import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

const document = new JSDOM(readFileSync(new URL('../dist/index.html', import.meta.url), 'utf8')).window.document;
const payload = JSON.parse(readFileSync(new URL('../src/data/jobs.json', import.meta.url), 'utf8'));
const retired = source => ['bebee', 'ashby'].includes(source) || source.startsWith('employer_');
const expected = payload.jobs.filter(job => job.status === 'ACTIVE'
  && job.eligibility_level !== 'RESTRICTED'
  && !(job.job_id.startsWith('himalayas:') && job.deadline_at && Date.parse(job.deadline_at) <= Date.now())
  && !retired(job.job_id.split(':')[0])
  && job.sources.some(source => !retired(source)));
const allCards = [...document.querySelectorAll('[data-source="all"] [data-job-id]')];
assert.deepEqual(allCards.map(card => card.dataset.jobId).sort(), expected.map(job => job.job_id).sort());
assert.equal(document.querySelector('[data-source="company_careers"], [data-source="ashby"]'), null);
assert.equal(document.querySelector('#direct-filter, #employer-filter, #sector-filter'), null);
assert.equal(document.querySelector('[data-employer], [data-direct], [data-sectors]'), null);
const panels = [...document.querySelectorAll('[data-source-group]')]
  .sort((a, b) => Number(a.style.order) - Number(b.style.order));
if (expected.length) assert.equal(panels[0].dataset.source, 'all');
const himalayas = document.querySelector('[data-source="himalayas"]');
assert(himalayas, 'Himalayas keeps its header and controls even when empty');
assert.equal(himalayas.querySelector('.source-provider a')?.href, 'https://himalayas.app/');
const expectedHimalayas = expected.filter(job => job.sources.includes('himalayas'));
const copies = new Map();
for (const card of document.querySelectorAll('[data-job-id]')) {
  const id = card.dataset.jobId;
  if (!copies.has(id)) copies.set(id, []);
  copies.get(id).push(card);
}
assert.deepEqual([...himalayas.querySelectorAll('[data-job-id]')].map(card => card.dataset.jobId).sort(),
  expectedHimalayas.map(job => job.job_id).sort());
for (const job of expectedHimalayas) {
  for (const card of copies.get(job.job_id) ?? []) {
    assert.equal(card.querySelector('.job-title')?.getAttribute('href'), job.preferred_apply_url);
    assert(card.querySelector('.source')?.textContent.includes('Himalayas'));
    if (job.source_updated_at && !job.published_at && !job.published_date) {
      assert(card.querySelector('.posted')?.textContent.includes('Updated:'));
    }
  }
}
for (const panel of panels) {
  assert(!retired(panel.dataset.source));
  assert(panel.querySelector('h3'));
  assert(panel.querySelector('[data-period="latest"]'));
  assert.equal(panel.querySelector('[data-source-feed] h3'), null);
  assert.equal(panel.querySelector('[data-source-feed] [data-period]'), null);
}
console.log(`Verified ${panels.length} source panels and ${allCards.length} accepted jobs; retired feeds and filters are absent.`);

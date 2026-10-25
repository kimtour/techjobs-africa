import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';
import { companyCareerJobs } from '../src/lib/company-careers.js';

const acceptedPath = process.argv[2];
if (!acceptedPath) throw new Error('Supply the accepted jobs.json used to build the site');
const accepted = JSON.parse(readFileSync(acceptedPath, 'utf8')).jobs;
const expected = companyCareerJobs(accepted);
const expectedIds = expected.map(job => job.job_id).sort();
const expectedJobs = new Map(expected.map(job => [job.job_id, job]));
const built = readFileSync(new URL('../dist/index.html', import.meta.url), 'utf8');

function verify(html, label) {
  const document = new JSDOM(html).window.document;
  const groups = [...document.querySelectorAll('[data-source-group]')]
    .sort((a, b) => Number(a.style.order) - Number(b.style.order));
  assert.deepEqual(groups.slice(0, 2).map(group => group.dataset.source), ['all', 'company_careers']);
  const company = groups[1];
  assert.equal(company.querySelector('h3').textContent, 'Company Career Page');
  assert.equal(company.querySelector('[data-source-feed] .source-heading'), null);
  assert.equal(company.querySelectorAll('[data-period]').length, 6);
  assert(company.querySelector('[data-source-status]'));
  const cards = [...company.querySelectorAll('[data-job-id]')];
  assert.deepEqual(cards.map(card => card.dataset.jobId).sort(), expectedIds);
  for (const card of cards) {
    assert.equal(card.querySelector('a.job-title').getAttribute('href'), expectedJobs.get(card.dataset.jobId).preferred_apply_url);
    assert.match(card.querySelector('.source').textContent, /^Source: /);
  }
  const allIds = [...groups[0].querySelectorAll('[data-job-id]')].map(card => card.dataset.jobId);
  assert.equal(new Set(allIds).size, allIds.length);
  assert(expectedIds.every(id => allIds.includes(id)));
  assert.equal(document.querySelector('a[href="/employers/"]'), null);
  console.log(`${label}: Company Career Page is second, with ${cards.length} accepted vacancies and original application/publisher links.`);
}

verify(built, 'Local build');
if (process.argv[3]) {
  const response = await fetch(process.argv[3], {signal: AbortSignal.timeout(20000)});
  assert(response.ok, `Site returned HTTP ${response.status}`);
  verify(await response.text(), 'Deployed site');
}

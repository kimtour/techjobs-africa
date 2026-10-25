import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

const script = readFileSync(new URL('../src/scripts/filters.js', import.meta.url), 'utf8');
const key = 'techkazi.openedJobs';
function setup(saved, blocked = false) {
  const card = id => `<article data-job-id="${id}"><a class="job-title" href="https://example.com/${id}" target="_blank"><span>${id}</span></a></article>`;
  const dom = new JSDOM(`<div data-source-feed>${card('a')}${card('b')}</div><div data-source-feed>${card('a')}</div>`, {
    url: 'https://techkazi.pages.dev/', runScripts: 'outside-only',
  });
  if (saved !== undefined) dom.window.localStorage.setItem(key, saved);
  if (blocked) Object.defineProperty(dom.window, 'localStorage', { get() { throw new Error('Blocked'); } });
  dom.window.eval(script);
  return { dom, links: [...dom.window.document.querySelectorAll('.job-title')] };
}

test('opening a job updates both copies, preserves navigation and feed positions, and survives reload', () => {
  const { dom, links } = setup();
  const feeds = [...dom.window.document.querySelectorAll('[data-source-feed]')];
  feeds[0].scrollTop = 120;
  feeds[1].scrollTop = 80;
  const click = new dom.window.MouseEvent('click', { bubbles: true, cancelable: true, ctrlKey: true });
  links[0].querySelector('span').dispatchEvent(click);
  assert.equal(click.defaultPrevented, false);
  assert.deepEqual(links.map(link => link.classList.contains('is-opened')), [true, false, true]);
  assert.deepEqual(feeds.map(feed => feed.scrollTop), [120, 80]);
  const saved = dom.window.localStorage.getItem(key);
  assert.deepEqual(JSON.parse(saved), ['a']);
  assert.deepEqual(setup(saved).links.map(link => link.classList.contains('is-opened')), [true, false, true]);
});

test('middle clicks mark jobs, while right clicks do not', () => {
  const { dom, links } = setup();
  links[0].dispatchEvent(new dom.window.MouseEvent('auxclick', { button: 2 }));
  assert.equal(links[0].classList.contains('is-opened'), false);
  const click = new dom.window.MouseEvent('auxclick', { button: 1, cancelable: true });
  links[0].dispatchEvent(click);
  assert.equal(click.defaultPrevented, false);
  assert.equal(links[2].classList.contains('is-opened'), true);
});

test('blocked or malformed storage does not prevent marking opened jobs', () => {
  for (const [saved, blocked] of [[undefined, true], ['invalid', false], ['{}', false], ['[null,123,"expired"]', false]]) {
    const { dom, links } = setup(saved, blocked);
    links[0].dispatchEvent(new dom.window.MouseEvent('click'));
    assert.equal(links[2].classList.contains('is-opened'), true);
    if (!blocked) assert.deepEqual(JSON.parse(dom.window.localStorage.getItem(key)), ['a']);
  }
});

test('other tabs and restored pages sync opened jobs without losing earlier clicks', () => {
  for (const eventType of ['storage', 'focus', 'pageshow']) {
    const { dom, links } = setup();
    links[0].click();
    dom.window.localStorage.setItem(key, '["b"]');
    const event = eventType === 'storage'
      ? new dom.window.StorageEvent('storage', { key })
      : new dom.window.Event(eventType);
    dom.window.dispatchEvent(event);
    assert(links.every(link => link.classList.contains('is-opened')), eventType);
    links[0].click();
    assert.deepEqual(JSON.parse(dom.window.localStorage.getItem(key)).sort(), ['a', 'b']);
  }
});

test('all ten feeds mark their job and every All Jobs copy, including loaded rows', () => {
  const sources = ['all', 'myjobmag', 'corporate_staffing', 'linkedin', 'fuzu', 'openedcareer', 'brightermonday', 'elevolt', 'ashby', 'company_careers'];
  const card = id => `<li data-source-card data-job-id="${id}"><a class="job-title" href="https://example.com/${id}" target="_blank">${id}</a></li>`;
  const group = source => `<section data-source-group data-source="${source}" data-limit="10"><div data-source-feed><ul>${Array.from({ length: 12 }, (_, i) => card(`${source === 'all' ? 'myjobmag' : source}-${i}`)).join('')}${source === 'all' ? sources.slice(2).map(s => card(`${s}-0`)).join('') : ''}</ul><button data-more>More</button></div><button data-period="month">Month</button><button data-period="latest">Latest</button></section>`;
  const dom = new JSDOM(sources.map(group).join(''), { url: 'https://techkazi.pages.dev/', runScripts: 'outside-only' });
  dom.window.HTMLElement.prototype.scrollTo = function() {};
  dom.window.eval(script);
  const doc = dom.window.document;
  for (const source of sources) {
    const feed = doc.querySelector(`[data-source="${source}"]`);
    feed.querySelector('[data-more]').click();
    const link = feed.querySelectorAll('.job-title')[source === 'all' ? 0 : 11];
    assert.equal(link.closest('[data-source-card]').hidden, false);
    link.click();
    const id = link.closest('[data-job-id]').dataset.jobId;
    const copies = [...doc.querySelectorAll('[data-job-id]')].filter(c => c.dataset.jobId === id);
    assert(copies.every(c => c.querySelector('.job-title').classList.contains('is-opened')), source);
    feed.querySelector('[data-period="month"]').click();
    feed.querySelector('[data-period="latest"]').click();
    assert(link.classList.contains('is-opened'), source);
    feed.querySelector('.job-title').click();
  }
  for (const source of sources.slice(1)) {
    const allCopy = doc.querySelector(`[data-source="all"] [data-job-id="${source}-0"] .job-title`);
    assert(allCopy.classList.contains('is-opened'), source);
  }
});

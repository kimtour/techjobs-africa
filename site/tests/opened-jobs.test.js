import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

const script = readFileSync(new URL('../public/filters.js', import.meta.url), 'utf8');
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

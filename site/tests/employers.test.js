import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

test('direct employer, employer and sector filters intersect and reset scrolling', () => {
  const dom = new JSDOM(`<form id="job-filters"><select id="direct-filter"><option value=""></option><option value="direct">Direct</option></select><select id="employer-filter"><option value=""></option><option value="a">A</option></select><select id="sector-filter"><option value=""></option><option>Banks</option></select></form><p id="job-count"></p><section data-source-group data-limit="20"><div data-source-feed>${[ ['a','true','Banks'], ['b','true','Energy'], ['','false','Banks'] ].map(([e,d,s],i) => `<li data-source-card data-job-id="${i}" data-employer="${e}" data-direct="${d}" data-sectors='["${s}"]'></li>`).join('')}</div></section>`, {url: 'https://techkazi.pages.dev/', runScripts: 'outside-only'});
  dom.window.HTMLElement.prototype.scrollTo = function() { this.scrollTop = 0; };
  dom.window.eval(readFileSync(new URL('../src/scripts/filters.js', import.meta.url), 'utf8'));
  const doc = dom.window.document;
  const shown = () => [...doc.querySelectorAll('[data-source-card]')].filter(c => !c.hidden).length;
  const select = (id, value) => { const el = doc.querySelector(id); el.value = value; el.dispatchEvent(new dom.window.Event('change')); };
  assert.equal(shown(), 3);
  select('#direct-filter', 'direct');
  assert.equal(shown(), 2);
  select('#sector-filter', 'Banks');
  assert.equal(shown(), 1);
  select('#employer-filter', 'a');
  assert.equal(shown(), 1);
  assert.equal(doc.querySelector('[data-source-group]').dataset.limit, '10');
});

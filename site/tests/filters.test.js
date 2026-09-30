import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

const script = readFileSync(new URL('../public/filters.js', import.meta.url), 'utf8');
const now = Date.parse('2026-09-30T12:00:00Z');
const day = 86400000;
function setup() {
  const source = (id) => `<section data-source-group data-source="${id}" data-limit="10">
    <h3>${id}</h3><div>${['latest', 'day', 'three-days', 'week', 'two-weeks', 'month'].map(p => `<button data-period="${p}" aria-pressed="${p === 'latest'}">${p}</button>`).join('')}</div>
    <p data-source-count></p><div data-source-feed tabindex="0">
    ${Array.from({length: 25}, (_, i) => `<article data-source-card data-search="Engineer ${i}" data-category="${i % 2 ? 'QA' : 'Software'}" data-published="${i === 24 ? '' : new Date(now - i * day).toISOString()}"></article>`).join('')}
    <p data-source-empty hidden></p><button data-more>Load more jobs</button></div><p data-source-status></p></section>`;
  const dom = new JSDOM(`<form id="job-filters"><input id="job-search"><select id="category-filter"><option value=""></option><option>QA</option></select></form><p id="job-count"></p><p id="no-results" hidden></p>${source('a')}${source('b')}`, {runScripts: 'outside-only'});
  dom.window.Date.now = () => now;
  dom.window.HTMLElement.prototype.scrollTo = function () { this.scrollTop = 0; };
  dom.window.eval(script);
  const doc = dom.window.document;
  const groups = [...doc.querySelectorAll('[data-source-group]')];
  return {dom, doc, groups};
}
const shown = group => [...group.querySelectorAll('[data-source-card]')].filter(c => !c.hidden).length;

test('load more changes only its own source and preserves scroll', () => {
  const {groups:[a,b]} = setup();
  a.querySelector('[data-source-feed]').scrollTop = 100;
  b.querySelector('[data-source-feed]').scrollTop = 50;
  assert.equal(shown(a), 10);
  a.querySelector('[data-more]').click();
  assert.equal(shown(a), 20);
  assert.equal(shown(b), 10);
  assert.equal(a.querySelector('[data-source-feed]').scrollTop, 100);
  assert.equal(b.querySelector('[data-source-feed]').scrollTop, 50);
  a.querySelector('[data-more]').click();
  assert.equal(shown(a), 25);
  assert.equal(a.querySelector('[data-more]').hidden, true);
});

test('bounded periods show all matching jobs while latest keeps its own pagination', () => {
  const {groups:[a,b]} = setup();
  b.querySelector('[data-more]').click();
  for (const [period, expected] of [['day',2],['three-days',4],['week',8],['two-weeks',15],['month',24],['latest',25]]) {
    a.querySelector(`[data-period="${period}"]`).click();
    assert.equal(Number(a.dataset.matching), expected);
    assert.equal(shown(a), period === 'latest' ? Math.min(expected,10) : expected);
    assert.equal(a.querySelector('[data-more]').hidden, period !== 'latest');
    assert.equal(shown(b),20);
    assert.equal(a.querySelectorAll('[aria-pressed="true"]').length,1);
  }
});

test('empty periods retain header and recovery controls; invalid and future dates are excluded', () => {
  const {groups:[a]} = setup();
  for (const [i,card] of [...a.querySelectorAll('[data-source-card]')].entries()) {
    card.dataset.published = i % 2 ? 'invalid' : '2027-01-01T00:00:00Z';
  }
  a.querySelector('[data-period="day"]').click();
  assert.equal(a.hidden,false);
  assert.equal(shown(a),0);
  assert.equal(a.querySelector('[data-source-empty]').hidden,false);
  a.querySelector('[data-period="latest"]').click();
  assert.equal(shown(a),10);
});

test('search/category intersect periods and reset pagination; form stays on page', () => {
  const {dom,doc,groups:[a,b]} = setup();
  a.querySelector('[data-more]').click();
  const search = doc.querySelector('#job-search');
  search.value='ENGINEER 1';
  search.dispatchEvent(new dom.window.Event('input'));
  assert.equal(a.dataset.limit,'10');
  assert.equal(Number(a.dataset.matching),11);
  const category=doc.querySelector('#category-filter');
  category.value='QA';
  category.dispatchEvent(new dom.window.Event('change'));
  assert.equal(Number(a.dataset.matching),6);
  assert.equal(Number(b.dataset.matching),6);
  search.value='no matches';
  search.dispatchEvent(new dom.window.Event('input'));
  assert.equal(doc.querySelector('#no-results').hidden,false);
  assert.equal(a.hidden,false);
  const submit=new dom.window.Event('submit',{cancelable:true});
  doc.querySelector('form').dispatchEvent(submit);
  assert.equal(submit.defaultPrevented,true);
});

test('search and category keep bounded periods fully expanded', () => {
  const {dom,doc,groups:[a]} = setup();
  a.querySelector('[data-period="month"]').click();
  assert.equal(shown(a),24);
  const search = doc.querySelector('#job-search');
  search.value='ENGINEER';
  search.dispatchEvent(new dom.window.Event('input'));
  assert.equal(shown(a),24);
  const category = doc.querySelector('#category-filter');
  category.value='QA';
  category.dispatchEvent(new dom.window.Event('change'));
  assert.equal(shown(a),12);
  assert.equal(a.querySelector('[data-more]').hidden,true);
});

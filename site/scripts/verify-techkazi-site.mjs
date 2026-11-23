import { appendFileSync, readFileSync } from "node:fs";
import { JSDOM } from "jsdom";

const origin = "https://techkazi.pages.dev";
const built = new JSDOM(readFileSync(new URL("../dist/index.html", import.meta.url), "utf8")).window.document;
const jobIds = document => [...document.querySelectorAll('[data-source="all"] [data-job-id]')]
  .map(card => card.getAttribute("data-job-id")).sort();
const expectedIds = jobIds(built);
if (!expectedIds.length) throw new Error("Refusing to verify an empty production job export");

async function verify() {
  const response = await fetch(`${origin}/`, { signal: AbortSignal.timeout(20000) });
  if (!response.ok) throw new Error(`TechKazi page returned HTTP ${response.status}`);
  const document = new JSDOM(await response.text()).window.document;
  if (document.querySelector('[data-source="company_careers"], [data-source="ashby"], #direct-filter, #employer-filter, #sector-filter')) {
    throw new Error("Retired feed panel or filters remain live");
  }
  if (document.title !== built.title || document.querySelector(".eyebrow")?.textContent !== "TechKazi") {
    throw new Error("Live TechKazi branding does not match the build");
  }
  for (const selector of ['link[rel="canonical"]', 'meta[property="og:url"]']) {
    const node = document.querySelector(selector);
    if ((node?.getAttribute("href") || node?.getAttribute("content")) !== `${origin}/`) {
      throw new Error("Live canonical or sharing address is incorrect");
    }
  }
  for (const [source, home] of [['jobicy', 'https://jobicy.com/'], ['remoteok', 'https://remoteok.com/']]) {
    const actual = document.querySelector(`[data-source="${source}"]`);
    const expected = built.querySelector(`[data-source="${source}"]`);
    if (!actual || actual.querySelector('.source-provider a')?.href !== home) {
      throw new Error(`${source} source panel/attribution missing`);
    }
    const links = p => [...p.querySelectorAll('[data-job-id]')].map(c =>
      [c.dataset.jobId, c.querySelector('.job-title')?.getAttribute('href')]).sort();
    if (JSON.stringify(links(actual)) !== JSON.stringify(links(expected))) {
      throw new Error(`${source} live jobs/links do not match build`);
    }
    for (const card of actual.querySelectorAll('[data-job-id]')) {
      if (card.querySelector('.job-title')?.relList.contains('nofollow')) {
        throw new Error(`${source} application link must be followed`);
      }
    }
  }
  const h = document.querySelector('[data-source="himalayas"]');
  const expectedH = built.querySelector('[data-source="himalayas"]');
  if (expectedH && (!h || h.querySelector('.source-provider a')?.href !== 'https://himalayas.app/')) {
    throw new Error("Himalayas panel or source attribution is missing");
  }
  if (h && expectedH) {
    const cards = panel => [...panel.querySelectorAll('[data-job-id]')].map(card =>
      [card.dataset.jobId, card.querySelector('.job-title')?.getAttribute('href')]).sort();
    if (JSON.stringify(cards(h)) !== JSON.stringify(cards(expectedH))) {
      throw new Error("Live Himalayas identities/application links do not match the build");
    }
  }
  if (JSON.stringify(jobIds(document)) !== JSON.stringify(expectedIds)) {
    throw new Error("Live job identities do not match the accepted production build");
  }
  for (const [path, evidence] of [
    ["robots.txt", `${origin}/sitemap.xml`],
    ["sitemap.xml", `<loc>${origin}/</loc>`],
    ["favicon.svg", 'xmlns="http://www.w3.org/2000/svg"'],
  ]) {
    const asset = await fetch(`${origin}/${path}`, { signal: AbortSignal.timeout(15000) });
    if (!asset.ok || !(await asset.text()).includes(evidence)) {
      throw new Error(`Live TechKazi ${path} is missing or incorrect`);
    }
  }
}

for (let attempt = 0; ; attempt++) {
  try { await verify(); break; }
  catch (error) {
    if (attempt === 5) throw error;
    console.log("Waiting for the new TechKazi deployment to become visible");
    await new Promise(resolve => setTimeout(resolve, 10000));
  }
}
const summary = `Verified TechKazi at ${origin}/ with all ${expectedIds.length} accepted visible jobs, canonical/sharing metadata, favicon, robots and sitemap.\n`;
console.log(summary.trim());
if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, summary);

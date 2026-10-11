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
  if (document.title !== built.title || document.querySelector(".eyebrow")?.textContent !== "TechKazi") {
    throw new Error("Live TechKazi branding does not match the build");
  }
  for (const selector of ['link[rel="canonical"]', 'meta[property="og:url"]']) {
    const node = document.querySelector(selector);
    if ((node?.getAttribute("href") || node?.getAttribute("content")) !== `${origin}/`) {
      throw new Error("Live canonical or sharing address is incorrect");
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

const form = document.querySelector("#directory-filters");
const search = document.querySelector("#directory-search");
const sector = document.querySelector("#directory-sector");
const cards = [...document.querySelectorAll("[data-employer-card]")];
const more = document.querySelector("#directory-more");
let limit = 40;
function filter() {
  const term = (search?.value ?? "").trim().toLowerCase();
  let matching = 0;
  for (const card of cards) {
    const matches = card.dataset.name.includes(term)
      && (!sector?.value || JSON.parse(card.dataset.sectors).includes(sector.value));
    if (matches) matching += 1;
    card.hidden = !matches || matching > limit;
  }
  document.querySelector("#directory-count").textContent = `Showing ${Math.min(limit, matching)} of ${matching} employer records`;
  document.querySelector("#directory-empty").hidden = matching !== 0;
  more.hidden = matching <= limit;
}
form?.addEventListener("submit", e => e.preventDefault());
for (const control of [search, sector]) control?.addEventListener(control === search ? "input" : "change", () => { limit = 40; filter(); });
more?.addEventListener("click", () => { limit += 40; filter(); });
filter();

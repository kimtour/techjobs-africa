const search = document.querySelector("#job-search");
const category = document.querySelector("#category-filter");
const groups = [...document.querySelectorAll("[data-source-group]")];
const count = document.querySelector("#job-count");
const noResults = document.querySelector("#no-results");

function matchesPeriod(card, period) {
  if (period === "latest") return true;
  const published = card.dataset.published;
  if (!published) return false;
  const publishedAt = new Date(published).getTime();
  if (Number.isNaN(publishedAt)) return false;
  const age = Date.now() - publishedAt;
  const ranges = {
    day: 24 * 60 * 60 * 1000,
    "three-days": 3 * 24 * 60 * 60 * 1000,
    week: 7 * 24 * 60 * 60 * 1000,
    "two-weeks": 14 * 24 * 60 * 60 * 1000,
    month: 30 * 24 * 60 * 60 * 1000,
  };
  return age <= ranges[period] && age >= 0;
}

function applyFilters(targetGroup) {
  const searchTerm = (search?.value ?? "").trim().toLocaleLowerCase();
  const selectedCategory = category?.value ?? "";

  for (const group of targetGroup ? [targetGroup] : groups) {
    const limit = Number(group.dataset.limit ?? "10");
    const period = group.dataset.period ?? "latest";
    const cards = [...group.querySelectorAll("[data-source-card]")];
    let matching = 0;

    for (const card of cards) {
      const matchesSearch = (card.dataset.search ?? "").toLocaleLowerCase().includes(searchTerm);
      const matchesCategory = !selectedCategory || card.dataset.category === selectedCategory;
      const matches = matchesSearch && matchesCategory && matchesPeriod(card, period);
      if (matches) matching += 1;
      card.hidden = !matches || matching > limit;
    }

    // Keep the header and controls available even when a period has no matches.
    group.dataset.matching = String(matching);
    const empty = group.querySelector("[data-source-empty]");
    if (empty) empty.hidden = matching !== 0;
    const status = group.querySelector("[data-source-status]");
    if (status) status.textContent = `Showing ${Math.min(limit, matching)} of ${matching} jobs${matching > 0 ? " · Scroll for more" : ""}`;
    const more = group.querySelector("[data-more]");
    if (more) more.hidden = matching <= limit;
    const sourceCount = group.querySelector("[data-source-count]");
    if (sourceCount) sourceCount.textContent = `${matching} listing${matching === 1 ? "" : "s"}`;
  }

  const visible = groups.reduce((total, group) => total + Number(group.dataset.matching ?? 0), 0);
  if (count) count.textContent = `${visible} active role${visible === 1 ? "" : "s"}`;
  if (noResults) noResults.hidden = visible !== 0;
}

function resetLimitForPeriod(group) {
  const period = group.dataset.period ?? "latest";
  group.dataset.limit = period === "latest"
    ? "10"
    : String(group.querySelectorAll("[data-source-card]").length);
}

for (const more of document.querySelectorAll("[data-more]")) {
  more.addEventListener("click", () => {
    const group = more.closest("[data-source-group]");
    if (group) group.dataset.limit = String(Number(group.dataset.limit ?? "10") + 10);
    applyFilters(group);
    if (more.hidden) group?.querySelector("[data-source-feed]")?.focus({ preventScroll: true });
  });
}

for (const periodButton of document.querySelectorAll("[data-period]")) {
  periodButton.addEventListener("click", () => {
    const group = periodButton.closest("[data-source-group]");
    if (!group) return;
    group.dataset.period = periodButton.dataset.period ?? "latest";
    resetLimitForPeriod(group);
    for (const button of group.querySelectorAll("[data-period]")) {
      button.setAttribute("aria-pressed", String(button === periodButton));
    }
    applyFilters(group);
    group.querySelector("[data-source-feed]")?.scrollTo(0, 0);
  });
}

function resetLimitsAndApplyFilters() {
  for (const group of groups) {
    resetLimitForPeriod(group);
    group.querySelector("[data-source-feed]")?.scrollTo(0, 0);
  }
  applyFilters();
}

document.querySelector("#job-filters")?.addEventListener("submit", (event) => event.preventDefault());
search?.addEventListener("input", resetLimitsAndApplyFilters);
category?.addEventListener("change", resetLimitsAndApplyFilters);
applyFilters();

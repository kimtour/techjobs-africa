const search = document.querySelector("#job-search");
const category = document.querySelector("#category-filter");
const groups = [...document.querySelectorAll("[data-source-group]")];
const count = document.querySelector("#job-count");
const noResults = document.querySelector("#no-results");

function applyFilters() {
  const searchTerm = (search?.value ?? "").trim().toLocaleLowerCase();
  const selectedCategory = category?.value ?? "";
  const filtering = Boolean(searchTerm || selectedCategory);
  let visible = 0;

  for (const group of groups) {
    const limit = Number(group.dataset.limit ?? "10");
    const cards = [...group.querySelectorAll("[data-source-card]")];
    let matching = 0;

    for (const card of cards) {
      const matchesSearch = (card.dataset.search ?? "").toLocaleLowerCase().includes(searchTerm);
      const matchesCategory = !selectedCategory || card.dataset.category === selectedCategory;
      const matches = matchesSearch && matchesCategory;
      if (matches) matching += 1;
      card.hidden = !matches || (!filtering && Number(card.dataset.index) >= limit);
    }

    group.hidden = matching === 0;
    const more = group.querySelector("[data-more]");
    if (more) more.hidden = filtering || matching <= limit;
    visible += matching;
  }

  if (count) count.textContent = `${visible} active role${visible === 1 ? "" : "s"}`;
  if (noResults) noResults.hidden = visible !== 0;
}

for (const more of document.querySelectorAll("[data-more]")) {
  more.addEventListener("click", () => {
    const group = more.closest("[data-source-group]");
    if (group) group.dataset.limit = String(Number(group.dataset.limit ?? "10") + 10);
    applyFilters();
  });
}

search?.addEventListener("input", applyFilters);
category?.addEventListener("change", applyFilters);
applyFilters();

const search = document.querySelector("#job-search");
const category = document.querySelector("#category-filter");
const cards = [...document.querySelectorAll(".job-card")];
const count = document.querySelector("#job-count");
const noResults = document.querySelector("#no-results");

function applyFilters() {
  const searchTerm = search.value.trim().toLocaleLowerCase();
  const selectedCategory = category.value;
  let visible = 0;

  for (const card of cards) {
    const matchesSearch = card.dataset.search.toLocaleLowerCase().includes(searchTerm);
    const matchesCategory = !selectedCategory || card.dataset.category === selectedCategory;
    const matches = matchesSearch && matchesCategory;
    card.hidden = !matches;
    if (matches) visible += 1;
  }
  count.textContent = `${visible} active role${visible === 1 ? "" : "s"}`;
  noResults.hidden = visible !== 0;
}

search?.addEventListener("input", applyFilters);
category?.addEventListener("change", applyFilters);

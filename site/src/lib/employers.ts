import registry from "../data/employers.json";

export const employers = registry.employers;
export const directoryEntries = registry.directory_entries;
export const employerSources = new Set(employers.flatMap(e => e.sources.map(s => s.id)));
export const employerById = new Map(employers.map(e => [e.id, e]));
export const sourceEmployers = new Map<string, typeof employers>();
for (const employer of employers) {
  for (const source of employer.sources) {
    sourceEmployers.set(source.id, [...(sourceEmployers.get(source.id) ?? []), employer]);
  }
}

export const sectorNames = [...new Set(employers.flatMap(e => e.sectors))].sort();

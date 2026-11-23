/** Filter old accepted exports until ingestion migrates the private snapshot.
 * @param {string} source
 */
const isRetiredSource = source => ['bebee', 'ashby'].includes(source) || source.startsWith('employer_');

/** @param {import('./jobs').Job} job */
export function retainedJob(job) {
  if (job.job_id.startsWith('himalayas:') && job.deadline_at
    && Date.parse(job.deadline_at) <= Date.now()) return null;
  if (isRetiredSource(job.job_id.split(':', 1)[0])) return null;
  const sources = job.sources.filter(source => !isRetiredSource(source));
  if (!sources.length) return null;
  return { ...job, sources };
}

const legacyCareerSources = new Set(['camunda', 'blacksmith', 'sdg']);

/** @param {import('./jobs').Job} job */
export const isDirectJob = (job) => job.direct_employer === true
  || job.sources.some(source => legacyCareerSources.has(source));

/** Only accepted vacancies are supplied by the build; registry links and trials are not inputs.
 * @param {import('./jobs').Job[]} acceptedJobs
 */
export const companyCareerJobs = (acceptedJobs) => acceptedJobs.filter(job =>
  job.status === 'ACTIVE' && job.eligibility_level !== 'RESTRICTED' && isDirectJob(job));

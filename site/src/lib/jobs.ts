import jobsPayload from "../data/jobs.json";

export type Job = {
  job_id: string;
  title: string;
  posting_company: string | null;
  hiring_company: string | null;
  city: string | null;
  country: string | null;
  workplace_type: string | null;
  category: string | null;
  eligibility_level: "CONFIRMED" | "LIKELY" | "VERIFY" | "RESTRICTED" | "UNKNOWN";
  published_at: string | null;
  published_date: string | null;
  preferred_apply_url: string;
  sources: string[];
  source_publisher?: string | null;
  status: "ACTIVE" | "STALE" | "CLOSED" | "EXPIRED";
};

type JobsPayload = {
  schema_version: number;
  jobs: Job[];
};

const payload = jobsPayload as JobsPayload;

export const jobs = payload.jobs
  .filter((job) => job.status === "ACTIVE"
    && !job.job_id.startsWith("bebee:")
    && job.sources.some((source) => source !== "bebee"))
  .map((job) => ({ ...job, sources: job.sources.filter((source) => source !== "bebee") }));

export const sourceOrder = [
  "myjobmag",
  "fuzu",
  "linkedin",
  "corporate_staffing",
  "openedcareer",
  "brightermonday",
  "elevolt",
  "ashby",
];

export const sourceName = (sourceId: string) =>
  ({
    all: "All Jobs",
    ashby: "TalentSafari",
    brightermonday: "BrighterMonday",
    corporate_staffing: "Corporate Staffing",
    elevolt: "Elevolt",
    fuzu: "Fuzu",
    linkedin: "LinkedIn",
    jsearch: "Google Jobs via JSearch",
    expertini: "Expertini (title from listing link)",
    careerjet: "Careerjet",
    myjobmag: "MyJobMag",
    openedcareer: "OpenedCareer",
  })[sourceId] ?? sourceId;

export const primarySource = (job: Job) =>
  sourceOrder.find((sourceId) => job.sources.includes(sourceId)) ?? job.sources[0];

export const locationLabel = (job: Job) =>
  [job.workplace_type, job.city, job.country].filter(Boolean).join(" · ") || "Location not listed";

export const companyLabel = (job: Job) => job.hiring_company || job.posting_company || "Company not listed";

export const postedLabel = (job: Job) => {
  if (job.published_date && !job.published_at) {
    const postedDate = new Date(`${job.published_date}T00:00:00Z`);
    if (!Number.isNaN(postedDate.getTime())) {
      return new Intl.DateTimeFormat("en-KE", { dateStyle: "medium", timeZone: "UTC" }).format(postedDate);
    }
  }
  if (!job.published_at) return "Posting date not published by source";
  const postedAt = new Date(job.published_at);
  if (Number.isNaN(postedAt.getTime())) return "Posting date not published by source";
  return `${new Intl.DateTimeFormat("en-KE", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Africa/Nairobi",
  }).format(postedAt)} EAT`;
};

// Missing/invalid dates stay last; use identity for deterministic ties.
export const newestFirst = (a: Job, b: Job) => {
  const timestamp = (job: Job) => {
    const value = Date.parse(job.published_at || job.published_date || "");
    return Number.isFinite(value) ? value : 0;
  };
  return timestamp(b) - timestamp(a) || a.job_id.localeCompare(b.job_id);
};

export const feedName = (sourceId: string) => sourceId === "linkedin" ? "Other/Google/Linkedin" : sourceName(sourceId);

export const sourceLabels = (job: Job) => job.sources.map((source) =>
  source === "jsearch" && job.source_publisher
    ? `${job.source_publisher} via Google Jobs / JSearch`
    : sourceName(source)
).join(", ");

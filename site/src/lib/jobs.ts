import jobsPayload from "../data/jobs.json";
import { sourceEmployers } from "./employers";
export { isDirectJob, companyCareerJobs } from "./company-careers.js";

export type Job = {
  job_id: string;
  title: string;
  posting_company: string | null;
  hiring_company: string | null;
  city: string | null;
  country: string | null;
  region?: string | null;
  workplace_type: string | null;
  category: string | null;
  eligibility_level: "CONFIRMED" | "LIKELY" | "VERIFY" | "RESTRICTED" | "UNKNOWN";
  published_at: string | null;
  published_date: string | null;
  preferred_apply_url: string;
  sources: string[];
  source_publisher?: string | null;
  status: "ACTIVE" | "STALE" | "CLOSED" | "EXPIRED";
  employer_id?: string | null;
  employer_sectors?: string[];
  direct_employer?: boolean;
  employment_type?: string | null;
  opportunity_type?: string | null;
  deadline_at?: string | null;
  last_checked_at?: string | null;
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
  "corporate_staffing",
  "linkedin",
  "fuzu",
  "openedcareer",
  "brightermonday",
  "elevolt",
  "ashby",
];

export const combinedSources = ["careerjet", "jsearch", "expertini", "camunda", "blacksmith", "sdg"];

export const sourceName = (sourceId: string) =>
  ({
    all: "All Jobs",
    company_careers: "Company Career Page",
    ashby: "TalentSafari",
    brightermonday: "BrighterMonday",
    corporate_staffing: "Corporate Staffing",
    elevolt: "Elevolt",
    fuzu: "Fuzu",
    linkedin: "LinkedIn",
    jsearch: "Google Jobs via JSearch",
    expertini: "Expertini",
    careerjet: "Careerjet",
    myjobmag: "MyJobMag",
    openedcareer: "OpenedCareer",
    camunda: "Camunda careers",
    blacksmith: "Blacksmith Agency careers",
    sdg: "Social Discovery Group careers",
  })[sourceId] ?? (sourceEmployers.has(sourceId)
    ? sourceEmployers.get(sourceId)?.length === 1
      ? `${sourceEmployers.get(sourceId)![0].name} careers` : "Shared employer board"
    : sourceId);

export const primarySource = (job: Job) =>
  sourceOrder.find((sourceId) => job.sources.includes(sourceId)) ?? job.sources[0];

export const locationLabel = (job: Job) =>
  [job.workplace_type, job.city, job.country || job.region].filter(Boolean).join(" · ") || "Location not listed";

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
  source === "expertini"
    ? (job.source_publisher === "Expertini RSS" ? "Expertini RSS" : "Expertini (title from listing link)")
    : ["jsearch", "camunda", "blacksmith", "sdg"].includes(source) && job.source_publisher
    ? (source === "jsearch" ? `${job.source_publisher} via Google Jobs / JSearch` : job.source_publisher)
    : sourceEmployers.has(source) && job.source_publisher
    ? job.source_publisher
    : sourceName(source)
).join(", ");

export const checkedDateLabel = (value: string) => new Intl.DateTimeFormat("en-KE", {
  dateStyle: "medium", timeStyle: "short", timeZone: "Africa/Nairobi",
}).format(new Date(value)) + " EAT";

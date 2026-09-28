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
  preferred_apply_url: string;
  sources: string[];
  status: "ACTIVE" | "STALE" | "CLOSED" | "EXPIRED";
};

type JobsPayload = {
  schema_version: number;
  jobs: Job[];
};

const payload = jobsPayload as JobsPayload;

export const jobs = payload.jobs.filter((job) => job.status === "ACTIVE");

export const sourceName = (sourceId: string) =>
  ({
    ashby: "TalentSafari",
    corporate_staffing: "Corporate Staffing",
    elevolt: "Elevolt",
    myjobmag: "MyJobMag",
    openedcareer: "OpenedCareer",
  })[sourceId] ?? sourceId;

export const locationLabel = (job: Job) =>
  [job.workplace_type, job.city, job.country].filter(Boolean).join(" · ") || "Location not listed";

export const companyLabel = (job: Job) => job.hiring_company || job.posting_company || "Company not listed";

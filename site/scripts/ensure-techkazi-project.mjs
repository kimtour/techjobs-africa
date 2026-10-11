// Hosting credentials remain in GitHub Secrets; never print API responses.
const { CLOUDFLARE_API_TOKEN: token, CLOUDFLARE_ACCOUNT_ID: account } = process.env;
if (!token || !account) throw new Error("Cloudflare deployment secrets are required");
const endpoint = `https://api.cloudflare.com/client/v4/accounts/${account}/pages/projects`;
const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };

async function request(url, options = {}) {
  const response = await fetch(url, {
    ...options, headers, signal: AbortSignal.timeout(20000),
  });
  const payload = await response.json();
  return { response, payload };
}

let { response, payload } = await request(`${endpoint}/techkazi`);
if (response.status === 404 || payload.errors?.some(error => error.code === 8000007)) {
  ({ response, payload } = await request(endpoint, {
    method: "POST", body: JSON.stringify({ name: "techkazi", production_branch: "main" }),
  }));
}
if (!response.ok || !payload.success) {
  const codes = (payload.errors || []).map(error => error.code).join(", ");
  throw new Error(`Cannot prepare TechKazi Pages project (HTTP ${response.status}, codes ${codes})`);
}
if (payload.result?.name !== "techkazi" || payload.result?.subdomain !== "techkazi.pages.dev") {
  throw new Error("The requested techkazi.pages.dev address was not assigned; keep the current hosting active");
}
console.log("TechKazi Pages project is ready at https://techkazi.pages.dev/");

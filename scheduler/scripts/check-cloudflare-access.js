if (!process.env.CLOUDFLARE_API_TOKEN || !process.env.CLOUDFLARE_ACCOUNT_ID) {
  throw new Error('Cloudflare account ID and API token must be configured in GitHub Secrets');
}
const headers = { Authorization: `Bearer ${process.env.CLOUDFLARE_API_TOKEN}` };
for (const path of ['workers/scripts', 'workers/subdomain']) {
  const response = await fetch(
    `https://api.cloudflare.com/client/v4/accounts/${process.env.CLOUDFLARE_ACCOUNT_ID}/${path}`,
    { headers, signal: AbortSignal.timeout(15000) },
  );
  const payload = await response.json();
  if (!response.ok || !payload.success) {
    const codes = (payload.errors || []).map(error => error.code).join(', ');
    throw new Error(`Cloudflare Worker access denied (HTTP ${response.status}, codes ${codes}). The existing token may only support Pages. Add Account: Workers Scripts Edit and Account Settings Read for this account, retaining its existing Pages Edit permission.`);
  }
  if (path.endsWith('subdomain') && !payload.result?.subdomain) {
    throw new Error('Register a workers.dev subdomain in the Cloudflare Workers dashboard before deploying');
  }
}
console.log('Cloudflare Workers API and workers.dev subdomain are accessible.');

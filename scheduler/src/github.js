export class GitHub {
  constructor(env, fetcher = fetch) {
    this.env = env;
    this.fetcher = fetcher;
  }

  async request(path, body) {
    // Cloudflare's global fetch rejects the GitHub instance as its receiver.
    const fetcher = this.fetcher;
    const response = await fetcher(
      `https://api.github.com/repos/${this.env.GITHUB_REPOSITORY}${path}`, {
        method: body ? 'POST' : 'GET',
        headers: {
          Authorization: `Bearer ${this.env.SCHEDULER_GITHUB_TOKEN}`,
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
          'User-Agent': 'techkazi-scheduler',
          'Content-Type': 'application/json',
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
        signal: AbortSignal.timeout(8000),
      });
    // Never record response bodies or exception messages, which may contain secrets.
    if (!response.ok) throw new Error(`github_http_${response.status}`);
    return response.status === 204 ? null : response.json();
  }

  runs() {
    return this.request(`/actions/workflows/${this.env.GITHUB_WORKFLOW}/runs?per_page=100`);
  }

  jobs(runId) {
    return this.request(`/actions/runs/${runId}/jobs?per_page=100`);
  }

  async claim(slot) {
    const file = encodeURIComponent(`${slot.replaceAll(':', '-')}.json`);
    try {
      const payload = await this.request(`/contents/state/scheduler-slots/${file}?ref=data`);
      return JSON.parse(atob(payload.content.replace(/\s/g, '')));
    } catch (error) {
      if (error.message === 'github_http_404') return null;
      throw error;
    }
  }

  dispatch(slot) {
    return this.request(`/actions/workflows/${this.env.GITHUB_WORKFLOW}/dispatches`, {
      ref: this.env.GITHUB_REF,
      inputs: { scheduler_slot: slot },
    });
  }

  alert(slot, kind) {
    return this.request('/actions/workflows/scheduler-alert.yml/dispatches', {
      ref: this.env.GITHUB_REF,
      inputs: { scheduler_slot: slot, alert_kind: kind },
    });
  }
}

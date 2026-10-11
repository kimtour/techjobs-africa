export const dashboard = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TechKazi · Fetch status</title>
<link rel="icon" type="image/svg+xml" href="https://techkazi.pages.dev/favicon.svg">
<style>
:root{color-scheme:light;font:16px/1.5 system-ui,sans-serif;color:#15242d;background:#f4f6f7}*{box-sizing:border-box}body{margin:0}main{max-width:1120px;margin:48px auto;padding:0 24px}h1{font-size:28px;letter-spacing:-.7px;margin:0 0 8px}p{margin:8px 0;color:#4c606d}a{color:#205d79}header{margin-bottom:24px}.summary{display:flex;gap:16px;flex-wrap:wrap;margin:24px 0}.card{background:#fff;border:1px solid #dce3e7;border-radius:8px;padding:16px 20px;flex:1;min-width:220px}.label{font-size:13px;color:#60727e;margin-bottom:6px}.value{font-size:18px;font-weight:600}.good{color:#176a48}.bad{color:#a2372a}.table{background:#fff;border:1px solid #dce3e7;border-radius:8px;overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px;white-space:nowrap}th,td{padding:12px 16px;text-align:left;border-bottom:1px solid #edf0f2}th{font-size:12px;color:#536775;text-transform:uppercase;letter-spacing:.04em}tr:last-child td{border:0}.note{font-size:13px;margin-top:16px}#error{color:#a2372a}footer{margin-top:24px;font-size:13px;color:#60727e}@media(max-width:600px){main{margin:24px auto;padding:0 16px}h1{font-size:24px}.summary{gap:8px}.card{min-width:100%}}
</style>
</head>
<body><main>
<header><h1>TechKazi · Fetch status</h1><p>Scheduled requests, actual source-fetch starts, and workflow results. All displayed times are East Africa Time (UTC+3).</p></header>
<div id="error" role="alert"></div>
<div class="summary">
<div class="card"><div class="label">Scheduler health</div><div id="health" class="value">Loading…</div></div>
<div class="card"><div class="label">Next scheduled fetch · EAT</div><div id="next" class="value">—</div></div>
<div class="card"><div class="label">Last scheduler check · EAT</div><div id="checked" class="value">—</div></div>
</div>
<p>Daily schedule: 01:00, 07:00, 09:00, 11:00, 13:00, 15:00, 17:00, 19:00, 21:00.</p>
<div class="table"><table><thead><tr><th>Scheduled · EAT</th><th>Fetch started · EAT</th><th>Result</th><th>Attempts</th><th>Alerts</th><th>Workflow</th></tr></thead><tbody id="records"></tbody></table></div>
<p class="note">Cloudflare checks every minute and catches up for up to 30 minutes. GitHub can still queue a workflow. A fetch that hasn’t started within ten minutes raises an alert. Showing the latest 90 slots.</p>
<footer><a href="https://techkazi.pages.dev/">TechKazi jobs</a> · <a href="https://github.com/kimtour/techjobs-africa/actions">All workflow runs</a> · <a href="/status">Status JSON</a> · <a href="/health">Health check</a> · Refreshes every 30 seconds</footer>
</main>
<script>
const format = value => value ? new Intl.DateTimeFormat('en-GB',{timeZone:'Africa/Nairobi',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(new Date(value)) : '—';
function cell(row,text){const element=document.createElement('td');element.textContent=text;row.append(element);return element;}
async function refresh(){
 try{
  const response=await fetch('/status',{cache:'no-store'});
  if(!response.ok)throw new Error('Status unavailable');
  const status=await response.json();
  document.getElementById('error').textContent=status.error ? 'GitHub connection problem: '+status.error : '';
  const health=document.getElementById('health');health.textContent=status.healthy?'Healthy':'Needs attention';health.className='value '+(status.healthy?'good':'bad');
  document.getElementById('next').textContent=format(status.next_fetch_at);
  document.getElementById('checked').textContent=format(status.last_tick_at);
  const records=document.getElementById('records');records.replaceChildren();
  for(const record of [...status.records].reverse()){
   const row=document.createElement('tr');
   cell(row,format(record.due_at)+(record.test?' · test':''));
   cell(row,format(record.fetch_started_at));
   cell(row,record.conclusion||record.status||'Pending');
   cell(row,String(record.attempts));
   const alerts=cell(row,Object.keys(record.alerts||{}).map(value=>value.replaceAll('_',' ')).join(', ')||'—');
   if(Object.keys(record.alerts||{}).length)alerts.className='bad';
   const linkCell=cell(row,'—');
   if(record.run_url&&record.run_url.startsWith('https://github.com/kimtour/techjobs-africa/actions/runs/')){const link=document.createElement('a');link.href=record.run_url;link.textContent='View run';linkCell.replaceChildren(link);}
   records.append(row);
  }
  if(!status.records.length){const row=document.createElement('tr');const td=cell(row,'No fetch slots recorded yet.');td.colSpan=6;records.append(row);}
 }catch{document.getElementById('error').textContent='Could not refresh status. Previously displayed results may be outdated.';}
}
refresh();setInterval(refresh,30000);
</script></body></html>`;

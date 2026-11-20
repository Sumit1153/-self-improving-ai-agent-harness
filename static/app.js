const $ = id => document.getElementById(id);
const fmt = n => typeof n === 'number' ? n.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '—';
const badge = yes => {
  const el = document.createElement('span');
  el.className = 'pill ' + (yes ? 'yes' : 'no');
  el.textContent = yes ? 'PASS' : 'FAIL';
  return el;
};
const el = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = String(text);
  if (className) node.className = className;
  return node;
};
async function api(path, options) {
  const res = await fetch(path, options);
  let data;
  try { data = await res.json(); } catch { throw new Error('Invalid server response'); }
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data));
  return data;
}
function post(path, body) { return api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); }
async function health() {
  try {
    const info = await api('/health');
    $('provider').textContent = 'Provider: ' + info.provider;
    $('connection').textContent = 'API online';
    $('model-name').textContent = info.model;
  } catch {
    $('connection').textContent = 'API offline';
    $('model-name').textContent = 'Unavailable';
  }
}
function renderRun(run) {
  $('last-status').textContent = run.success ? 'Passed' : 'Failed';
  $('last-attempts').textContent = run.attempts.length;
  $('last-tokens').textContent = fmt(run.total_tokens);
  const badgeEl = $('trace-badge');
  badgeEl.textContent = run.success ? 'COMPLETED' : 'NEEDS REVIEW';
  badgeEl.className = 'chip ' + (run.success ? 'good' : 'bad');
  const out = $('output'); out.replaceChildren();
  const answer = el('div', undefined, 'run-answer');
  answer.append(el('small', 'FINAL ANSWER'), el('div', run.answer || '(No answer generated)'));
  out.append(answer, el('div', `${run.attempts.length} attempt(s) · ${fmt(run.total_latency_ms)} ms · ${run.total_tokens} tokens`, 'trace-note'));
  for (const a of run.attempts) {
    const div = el('div', undefined, 'trace-attempt');
    const top = el('div', undefined, 'trace-top');
    top.append(el('strong', 'Attempt ' + a.number), el('span', `${fmt(a.latency_ms)} ms · ${a.tokens} tokens`));
    div.append(top);
    const details = [
      ['Plan', a.plan ? `${a.plan.tool}${a.plan.tool_input ? ' → ' + a.plan.tool_input : ''}` : 'Invalid plan'],
      ['Tool output', a.tool_output || 'None'],
      ['Answer', a.answer || 'None'],
      ['Evaluation', a.feedback]
    ];
    for (const [label, value] of details) {
      const line = el('div', undefined, 'trace-row');
      line.append(el('b', label + ': '), document.createTextNode(value));
      div.append(line);
    }
    div.append(badge(a.passed)); out.append(div);
  }
}
$('run-form').addEventListener('submit', async event => {
  event.preventDefault();
  const btn = $('run-button'); btn.disabled = true; btn.textContent = 'Running agent...';
  try {
    const expected = $('expected').value.trim();
    const run = await post('/agent/run', {
      task: $('task').value.trim(),
      expected_answer: expected || null,
      match_type: $('match').value,
      max_attempts: Number($('max-attempts').value)
    });
    renderRun(run); await history();
  } catch (error) { $('output').replaceChildren(el('p', 'Error: ' + error.message)); }
  finally { btn.disabled = false; btn.textContent = '▶   Execute agent'; }
});
document.querySelectorAll('.sample').forEach(btn => btn.addEventListener('click', () => {
  $('task').value = btn.dataset.task;
  $('expected').value = btn.dataset.answer;
  $('match').value = btn.dataset.match;
}));
async function benchmark() {
  const btn = $('benchmark-button'); btn.disabled = true; btn.textContent = 'Benchmark running...';
  const out = $('benchmark-output'); out.replaceChildren(el('div', 'Running comparison...'));
  try {
    const report = await post('/benchmark/run', { limit: 6, max_attempts: 3 });
    out.replaceChildren();
    const metrics = el('div', undefined, 'metrics');
    for (const [label, value] of [['Baseline success', report.baseline_success_rate + '%'], ['Harness success', report.harness_success_rate + '%'], ['Baseline avg latency', fmt(report.baseline_avg_latency_ms) + ' ms'], ['Harness avg latency', fmt(report.harness_avg_latency_ms) + ' ms']]) {
      const box = el('div', undefined, 'metric'); box.append(el('span', label), el('strong', value)); metrics.append(box);
    }
    out.append(metrics, el('p', `Average token consumption — baseline: ${report.baseline_avg_tokens}, harness: ${report.harness_avg_tokens}.`, 'hint'));
    const wrap = el('div', undefined, 'table-wrap'); const table = el('table'); const thead = el('thead'); const hdr = el('tr');
    for (const title of ['Benchmark task', 'Baseline', 'Harness', 'Attempts']) hdr.append(el('th', title));
    thead.append(hdr); table.append(thead);
    const tbody = el('tbody');
    for (const item of report.results) {
      const tr = el('tr'); tr.append(el('td', item.task));
      const base = el('td'); base.append(badge(item.baseline_passed)); tr.append(base);
      const harness = el('td'); harness.append(badge(item.harness_passed)); tr.append(harness, el('td', item.harness_attempts));
      tbody.append(tr);
    }
    table.append(tbody); wrap.append(table); out.append(wrap);
    await history();
  } catch (error) { out.replaceChildren(el('p', 'Error: ' + error.message)); }
  finally { btn.disabled = false; btn.textContent = 'Run 6 sample tasks'; }
}
$('benchmark-button').addEventListener('click', benchmark);
async function history() {
  const out = $('history-output');
  try {
    const runs = await api('/runs?limit=10'); out.replaceChildren();
    if (!runs.length) { out.append(el('div', 'No runs saved yet.', 'placeholder')); return; }
    for (const run of runs) {
      const line = el('div', undefined, 'history-item'); const info = el('div');
      info.append(el('strong', run.task), el('small', `${run.provider} · ${run.attempts_count} attempt(s) · ${fmt(run.total_latency_ms)} ms`));
      line.append(info, badge(run.success)); out.append(line);
    }
  } catch (error) { out.replaceChildren(el('p', 'Error: ' + error.message)); }
}
$('refresh-history').addEventListener('click', history);
health(); history();

// Rocky Ridge Lights request recorder.
// Runs on GitHub Actions during show hours. Every POLL_MS it reads Remote Falcon's public
// viewer API and counts (a) each song that newly appears in the request queue and
// (b) each song that starts playing. Totals are saved to stats.json, which the page reads.
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { execSync } from 'node:child_process';

const SHOW = 'rockyridgelights';
const API = process.env.RF_API || 'https://remotefalcon.com/remote-falcon-viewer/graphql';
const POLL_MS = Number(process.env.POLL_MS || 15_000);
const SAVE_EVERY_MS = 10 * 60_000;          // commit at most every 10 minutes
const MAX_RUN_MS = (Number(process.env.MAX_HOURS || 5.6)) * 3600_000; // Actions jobs stop at 6h
const OFF_GRACE_MS = Number(process.env.OFF_GRACE_MS || 20 * 60_000);          // stop 20 min after the show turns off
const NOT_STARTED_MS = 3 * 3600_000;        // stop if the show never turns on within 3h
const FILE = 'stats.json';
const TZ = 'America/New_York';

const QUERY = `query G($s: String!) { getShow(showSubdomain: $s) {
  playingNow playingNowSequence { name }
  preferences { viewerControlEnabled }
  requests { position sequence { name } }
} }`;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const etParts = (d) => Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', hour12: false })
  .formatToParts(d).map((p) => [p.type, p.value]));
/** Show night = Eastern date, rolling over at 6 AM so a show past midnight stays on one night. */
function nightKey(d = new Date()) { const p = etParts(new Date(d.getTime() - 6 * 3600_000)); return `${p.year}-${p.month}-${p.day}`; }

function load() {
  const empty = { updated: null, months: {} };
  if (!existsSync(FILE)) return empty;
  try { const j = JSON.parse(readFileSync(FILE, 'utf8')); j.months ??= {}; delete j.seasons; return j; } catch { return empty; }
}
/** Stats are kept per month (by show night, YYYY-MM) so test nights and Halloween/Christmas never mix. */
function bucket(stats, night) {
  const mk = night.slice(0, 7);
  const s = (stats.months[mk] ??= { requests: {}, plays: {}, totalRequests: 0, nights: {} });
  const n = (s.nights[night] ??= { requests: {}, plays: {}, totalRequests: 0 });
  return { s, n };
}
const bump = (obj, k) => { obj[k] = (obj[k] || 0) + 1; };

async function getShow() {
  const r = await fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json', 'User-Agent': 'rockyridgelights-recorder' },
    body: JSON.stringify({ query: QUERY, variables: { s: SHOW } }) });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  const j = await r.json();
  if (!j?.data?.getShow) throw new Error('no show');
  return j.data.getShow;
}

function commit(msg) {
  if (process.env.NO_COMMIT) return;
  try {
    execSync(`git add ${FILE}`);
    if (!execSync('git diff --cached --name-only').toString().trim()) return;
    execSync(`git -c user.name="RRL recorder" -c user.email="actions@users.noreply.github.com" commit -q -m "${msg}"`);
    for (let i = 0; i < 3; i++) {
      try { execSync('git pull -q --rebase origin main && git push -q origin HEAD:main', { stdio: 'inherit' }); return; }
      catch { execSync('sleep 5'); }
    }
  } catch (e) { console.error('commit failed', e.message); }
}

const stats = load();
const started = Date.now();
let prevQueue = null, prevPlaying = null, wasOn = false, offSince = null, lastSave = Date.now(), dirty = false, errors = 0;

while (Date.now() - started < MAX_RUN_MS) {
  try {
    const show = await getShow(); errors = 0;
    const on = !!show.preferences?.viewerControlEnabled;
    const night = nightKey();
    const { s, n } = bucket(stats, night);
    const queue = new Set((show.requests || []).map((q) => q.sequence?.name).filter(Boolean));
    if (prevQueue) {
      for (const name of queue) if (!prevQueue.has(name)) {
        bump(s.requests, name); bump(n.requests, name); s.totalRequests++; n.totalRequests++; dirty = true;
        console.log(new Date().toISOString(), 'request', name);
      }
    }
    const playing = show.playingNowSequence?.name || show.playingNow || '';
    if (prevPlaying !== null && playing && playing !== prevPlaying) {
      bump(s.plays, playing); bump(n.plays, playing); dirty = true;
      console.log(new Date().toISOString(), 'play', playing);
    }
    prevQueue = queue; prevPlaying = playing;

    if (on) { wasOn = true; offSince = null; }
    else if (wasOn) { offSince ??= Date.now(); if (Date.now() - offSince > OFF_GRACE_MS) break; }
    else if (Date.now() - started > NOT_STARTED_MS) { console.log('show never turned on'); break; }
  } catch (e) {
    errors++; console.error('poll error', e.message);
  }
  if (dirty && Date.now() - lastSave > SAVE_EVERY_MS) {
    stats.updated = new Date().toISOString(); writeFileSync(FILE, JSON.stringify(stats, null, 1));
    commit(`Update request stats ${nightKey()}`); lastSave = Date.now(); dirty = false;
  }
  await sleep(POLL_MS * Math.min(4, Math.max(1, errors)));
}
if (dirty) { stats.updated = new Date().toISOString(); writeFileSync(FILE, JSON.stringify(stats, null, 1)); commit(`Update request stats ${nightKey()}`); }
console.log('done');

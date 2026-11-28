#!/usr/bin/env python3
"""Rocky Ridge Lights request recorder, running on the FPP player.

Every 15 seconds it reads Remote Falcon's public viewer API and counts
(a) each song that newly appears in the request queue and (b) each song that starts playing.
Totals are saved to stats.json in the GitHub repo (every 10 minutes at most), which the
viewer page reads for "Hot tonight" and "Fan favorites".

Started each show night by rrl_recorder.sh from the FPP schedule. Stops 20 minutes after
Viewer Control turns off, or at 10:30 PM if the show never turned on.

  python3 rrl_recorder.py          record tonight
  python3 rrl_recorder.py --test   check the token and Remote Falcon once, then exit
"""
import base64, json, os, re, sys, time, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SHOW = 'rockyridgelights'
RF_API = 'https://remotefalcon.com/remote-falcon-viewer/graphql'
REPO = 'mryan231991/rockyridgelights'
FILE = 'stats.json'
BRANCH = 'main'
POLL_S = 15
SAVE_EVERY_S = 10 * 60      # GitHub Pages rebuilds on every save; keep it to ~6/hour
OFF_GRACE_S = 20 * 60       # stop 20 minutes after Viewer Control turns off
GIVE_UP_MIN = 22 * 60 + 30  # if the show hasn't turned on by 10:30 PM, the night is over
MAX_RUN_S = 9 * 3600        # safety net
TZ = ZoneInfo('America/New_York')
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(HERE, 'rrl_token.sh')

QUERY = """query G($s: String!) { getShow(showSubdomain: $s) {
  playingNow playingNowSequence { name }
  preferences { viewerControlEnabled }
  requests { position sequence { name } }
} }"""


def log(*a):
    print(datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S'), *a, flush=True)


def read_token():
    try:
        txt = open(TOKEN_FILE).read()
    except OSError:
        return ''
    m = re.search(r'GITHUB_TOKEN\s*=\s*["\']?([^"\'\s]*)', txt)
    return m.group(1) if m else ''


TOKEN = read_token()


def http(method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        'User-Agent': 'rockyridgelights-fpp-recorder', 'Content-Type': 'application/json', **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b'null')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b'null')
        except ValueError:
            return e.code, None


def gh(method, path, body=None):
    return http(method, f'https://api.github.com/repos/{REPO}{path}', body, {
        'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'})


def gh_load():
    """Returns (stats, sha) for stats.json on GitHub."""
    code, j = gh('GET', f'/contents/{FILE}?ref={BRANCH}')
    if code == 404:
        return {'updated': None, 'months': {}}, None
    if code != 200:
        raise RuntimeError(f'GitHub read failed: HTTP {code} {j and j.get("message")}')
    try:
        stats = json.loads(base64.b64decode(j['content']))
    except ValueError:
        stats = {}
    stats.setdefault('months', {})
    return stats, j['sha']


sha = None


def gh_save(stats, msg):
    global sha
    content = base64.b64encode((json.dumps(stats, indent=1) + '\n').encode()).decode()
    for _ in range(3):
        body = {'message': msg, 'content': content, 'branch': BRANCH,
                'committer': {'name': 'RRL recorder (FPP)', 'email': 'actions@users.noreply.github.com'}}
        if sha:
            body['sha'] = sha
        code, j = gh('PUT', f'/contents/{FILE}', body)
        if code in (200, 201):
            sha = j['content']['sha']
            log('saved', msg)
            return True
        if code in (409, 422):  # file changed on GitHub; take the new version id and write ours
            try:
                _, sha = gh_load()
            except Exception as e:
                log('reload failed', e)
            continue
        log('save failed: HTTP', code, j and j.get('message'))
        time.sleep(5)
    return False


def get_show():
    code, j = http('POST', RF_API, {'query': QUERY, 'variables': {'s': SHOW}})
    if code != 200 or not (j and j.get('data') and j['data'].get('getShow')):
        raise RuntimeError(f'Remote Falcon: HTTP {code}')
    return j['data']['getShow']


def et_now():
    return datetime.now(TZ)


def night_key():
    """Show night = Eastern date, rolling over at 6 AM so a show past midnight stays on one night."""
    return (et_now() - timedelta(hours=6)).strftime('%Y-%m-%d')


def past_show():
    n = et_now()
    m = n.hour * 60 + n.minute
    return m >= GIVE_UP_MIN or m < 6 * 60


def bucket(stats, night):
    s = stats['months'].setdefault(night[:7], {'requests': {}, 'plays': {}, 'totalRequests': 0, 'nights': {}})
    for k, v in (('requests', {}), ('plays', {}), ('totalRequests', 0), ('nights', {})):
        s.setdefault(k, v)
    n = s['nights'].setdefault(night, {'requests': {}, 'plays': {}, 'totalRequests': 0})
    return s, n


def bump(d, k):
    d[k] = d.get(k, 0) + 1


def stamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def test():
    ok = True
    if not TOKEN or 'paste' in TOKEN.lower():
        log('TOKEN: missing. Put it in', TOKEN_FILE)
        ok = False
    else:
        code, j = gh('GET', '')
        perms = (j or {}).get('permissions', {})
        if code != 200:
            log('TOKEN: GitHub said HTTP', code, (j or {}).get('message'))
            ok = False
        else:
            try:
                stats, s = gh_load()
                log('TOKEN: can read stats.json, months:', list(stats['months']) or 'none')
            except Exception as e:
                log('TOKEN:', e); ok = False
            log('TOKEN: push permission' if perms.get('push') else 'TOKEN: no write permission (needs Contents: Read and write)')
            ok = ok and bool(perms.get('push'))
    try:
        show = get_show()
        log('REMOTE FALCON: ok, viewer control', 'ON' if show['preferences']['viewerControlEnabled'] else 'off',
            '| playing:', (show.get('playingNowSequence') or {}).get('name') or show.get('playingNow') or 'nothing',
            '| queue:', len(show.get('requests') or []))
    except Exception as e:
        log('REMOTE FALCON:', e); ok = False
    log('TEST PASSED' if ok else 'TEST FAILED')
    return 0 if ok else 1


def main():
    global sha
    if not TOKEN or 'paste' in TOKEN.lower():
        log('no GitHub token in', TOKEN_FILE, '- not recording'); return 1
    stats, sha = gh_load()
    started = time.time()
    prev_queue = prev_playing = None
    was_on = False
    off_since = None
    last_save = time.time()
    dirty = False
    errors = 0
    log('recorder started for night', night_key())
    while time.time() - started < MAX_RUN_S:
        try:
            show = get_show(); errors = 0
            on = bool((show.get('preferences') or {}).get('viewerControlEnabled'))
            night = night_key()
            s, n = bucket(stats, night)
            queue = {(q.get('sequence') or {}).get('name') for q in (show.get('requests') or [])} - {None, ''}
            if prev_queue is not None:
                for name in queue - prev_queue:
                    bump(s['requests'], name); bump(n['requests'], name)
                    s['totalRequests'] += 1; n['totalRequests'] += 1; dirty = True
                    log('request', name)
            playing = (show.get('playingNowSequence') or {}).get('name') or show.get('playingNow') or ''
            if prev_playing is not None and playing and playing != prev_playing:
                bump(s['plays'], playing); bump(n['plays'], playing); dirty = True
                log('play', playing)
            prev_queue, prev_playing = queue, playing

            if on:
                if not was_on: log('viewer control is on')
                was_on, off_since = True, None
            elif was_on:
                off_since = off_since or time.time()
                if time.time() - off_since > OFF_GRACE_S:
                    log('show is over'); break
            elif past_show():
                log('show is off and it is past 10:30 PM; nothing to record'); break
        except Exception as e:
            errors += 1
            log('poll error', e)
        if dirty and time.time() - last_save > SAVE_EVERY_S:
            stats['updated'] = stamp()
            if gh_save(stats, f'Update request stats {night_key()}'):
                dirty = False
            last_save = time.time()
        time.sleep(POLL_S * min(4, max(1, errors)))
    if dirty:
        stats['updated'] = stamp()
        gh_save(stats, f'Update request stats {night_key()}')
    log('done')
    return 0


if __name__ == '__main__':
    sys.exit(test() if '--test' in sys.argv else main())

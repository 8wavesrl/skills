#!/usr/bin/env python3
"""Read-only check: can Codex take a review round right now?

Reports whether the codex CLI is installed and logged in, and the usage limits Codex recorded
in its most recent session log. It makes no call and spends no quota. The limits are a
snapshot from the last call: a window whose reset time has passed since then counts as fresh.

Usage: python3 codex_status.py [--threshold PERCENT] [--json]
Exit code: 0 when a Codex round can start (available, or unknown: no snapshot to judge by),
1 when it cannot (low, exhausted, not-logged-in, not-installed).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

CODEX_HOME = Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')
SESSIONS = CODEX_HOME / 'sessions'
# Newest session logs scanned for a usage snapshot; anything older says nothing about today.
MAX_LOGS = 20
# A round over many files spends several points of the 5 hour window: above this share it is
# likely to die halfway, with an empty answer file and nothing to show for the wait.
DEFAULT_THRESHOLD = 90


def parse_time(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (AttributeError, ValueError):
        return None


def latest_snapshot():
    """The newest usage snapshot across the newest session logs, with the time it was logged.

    Concurrent sessions interleave, so the most recently written file does not always hold the
    most recent snapshot: compare the event timestamps instead of stopping at the first file.
    """
    logs = sorted(SESSIONS.glob('*/*/*/rollout-*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)
    best, best_at = None, None
    for log in logs[:MAX_LOGS]:
        with log.open(errors='ignore') as f:
            for line in f:
                if '"rate_limits"' not in line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get('payload')
                limits = payload.get('rate_limits') if isinstance(payload, dict) else None
                # Several limit ids are logged; only the ones with windows carry usage.
                if not limits or not (limits.get('primary') or limits.get('secondary')):
                    continue
                at = parse_time(event.get('timestamp')) or log.stat().st_mtime
                if best_at is None or at > best_at:
                    best, best_at = limits, at
    return best, best_at


def window_label(minutes):
    if not minutes:
        return '?'
    return f'{minutes // 60}h' if minutes < 1440 else f'{minutes // 1440}d'


def windows_of(limits, now):
    windows = []
    for key in ('primary', 'secondary'):
        w = limits.get(key)
        if not w:
            continue
        resets_at = w.get('resets_at')
        logged = w.get('used_percent') or 0
        # Restarted after the snapshot: the best estimate is a fresh window, but other sessions
        # or devices may have spent some of it since, so say so instead of claiming 0%.
        reset = bool(resets_at and resets_at <= now)
        windows.append({'window': window_label(w.get('window_minutes')),
                        'used_percent': 0 if reset else logged, 'logged_percent': logged,
                        'reset_since_snapshot': reset, 'resets_at': resets_at})
    return windows


def status(threshold):
    if not shutil.which('codex'):
        return {'verdict': 'not-installed'}
    try:
        login = subprocess.run(['codex', 'login', 'status'], capture_output=True, text=True,
                               timeout=20, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return {'verdict': 'unknown', 'login': 'codex login status timed out'}
    if login.returncode != 0:
        return {'verdict': 'not-logged-in'}

    limits, snapshot_at = latest_snapshot()
    if not limits:
        # API-key accounts, or no call yet: nothing to judge by, the answer file decides.
        return {'verdict': 'unknown', 'login': (login.stdout or login.stderr).strip()}

    now = time.time()
    windows = windows_of(limits, now)
    credits = limits.get('credits') or {}
    worst = max((w['used_percent'] for w in windows), default=0)
    # The logged reached flag does not say which window it was: trust it only until a window
    # resets, then judge by the shares, or the weekly window would keep it standing for days.
    reached = limits.get('rate_limit_reached_type') and not any(
        w['reset_since_snapshot'] for w in windows)
    if credits.get('unlimited'):
        verdict = 'available'
    elif reached or worst >= 100:
        verdict = 'exhausted'
    elif worst >= threshold:
        verdict = 'low'
    else:
        verdict = 'available'
    return {'verdict': verdict, 'login': (login.stdout or login.stderr).strip(), 'windows': windows,
            'plan': limits.get('plan_type'), 'snapshot_at': snapshot_at}


def fmt_time(ts):
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else '?'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD,
                        help=f'used share of a window that counts as low (default {DEFAULT_THRESHOLD})')
    parser.add_argument('--json', action='store_true', help='print the result as JSON')
    args = parser.parse_args()

    result = status(args.threshold)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"codex: {result['verdict']}")
        if result.get('login'):
            print(f"  login: {result['login']}")
        for w in result.get('windows', []):
            if w['reset_since_snapshot']:
                print(f"  {w['window']} window: reset since the snapshot ({w['logged_percent']:.0f}% before)")
            else:
                print(f"  {w['window']} window: {w['used_percent']:.0f}% used, resets {fmt_time(w['resets_at'])}")
        if result.get('snapshot_at'):
            print(f"  snapshot logged at {fmt_time(result['snapshot_at'])}")
    sys.exit(0 if result['verdict'] in ('available', 'unknown') else 1)


if __name__ == '__main__':
    main()

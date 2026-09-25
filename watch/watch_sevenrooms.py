#!/usr/bin/env python3
"""Watch SevenRooms restaurants for bookable tables (last-minute cancellations).

Checks every party size and date in the window, and alerts only on slots not
seen before. Run by launchd (see com.kenpang.restaurant-watch.plist).
"""
import json
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

VENUES = {
    "wing": ("Wing", "https://www.sevenrooms.com/explore/wing/reservations/create/search/"),
}
PARTY_SIZES = range(1, 9)
DAYS_AHEAD = 60
WINDOW = 3  # the API accepts num_days of 1 or 3

HERE = Path(__file__).resolve().parent
STATE = HERE / "seen_slots.json"
LOG = HERE / "watch.log"
API = ("https://www.sevenrooms.com/api-yoa/availability/widget/range?venue={v}"
       "&time_slot=19:00&party_size={p}&halo_size_interval=100"
       "&start_date={d}&num_days={n}&channel=SEVENROOMS_WIDGET")


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    with LOG.open("a") as f:
        f.write(line + "\n")


def fetch(venue, party, start, tries=4):
    url = API.format(v=venue, p=party, d=start.isoformat(), n=WINDOW)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            if data.get("status") == 200:
                return data["data"]["availability"]
            err = str(data)[:150]
        except Exception as e:
            err = str(e)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{venue} p{party} {start}: {err}")


def bookable(venue):
    """Return (set of (date, shift, time, party) instantly bookable, number of failed queries)."""
    found, failed = set(), 0
    today = date.today()
    for party in PARTY_SIZES:
        for offset in range(0, DAYS_AHEAD, WINDOW):
            start = today + timedelta(days=offset)
            try:
                avail = fetch(venue, party, start)
            except Exception as e:
                failed += 1
                log(f"  query failed: {e}")
                continue
            for day, shifts in avail.items():
                for shift in shifts:
                    for t in shift.get("times", []):
                        if t.get("type") == "book":
                            found.add((day, shift.get("name", "").strip(), t["time"], party))
            time.sleep(1)
    return found, failed


def notify(title, body):
    subprocess.run(["osascript", "-e",
                    'on run argv\n display notification (item 2 of argv) with title (item 1 of argv) sound name "Glass"\n end run',
                    title, body], check=False)


def main():
    seen = json.loads(STATE.read_text()) if STATE.exists() else {}
    for venue, (name, url) in VENUES.items():
        slots, failed = bookable(venue)
        keys = {f"{d}|{s}|{t}|{p}" for d, s, t, p in slots}
        new = sorted(keys - set(seen.get(venue, [])))
        # After a partial run, keep old slots too so they don't re-alert next time
        seen[venue] = sorted(keys | set(seen.get(venue, [])) if failed else keys)
        log(f"{name}: {len(keys)} bookable slot(s), {len(new)} new" + (f", {failed} failed queries" if failed else ""))
        if new:
            # Summarise by date/time with the party sizes that fit
            by_slot = {}
            for k in new:
                d, s, t, p = k.split("|")
                by_slot.setdefault((d, t), []).append(int(p))
            lines = [f"{datetime.fromisoformat(d):%a %d %b} {t} (up to {max(ps)} ppl)"
                     for (d, t), ps in sorted(by_slot.items())]
            for line in lines:
                log(f"  NEW {name}: {line}")
            notify(f"{name}: table available!", "; ".join(lines[:4]) + (" …" if len(lines) > 4 else ""))
            with (HERE / "ALERTS.md").open("a") as f:
                f.write(f"\n## {datetime.now():%Y-%m-%d %H:%M} {name}\n{url}\n" + "\n".join(f"- {l}" for l in lines) + "\n")
    STATE.write_text(json.dumps(seen, indent=1))


if __name__ == "__main__":
    sys.exit(main())

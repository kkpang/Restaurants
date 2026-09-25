#!/usr/bin/env python3
"""Watch The Chairman's public booking page without holding or booking tables."""
import json
import sys
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlparse

from watch_sevenrooms import HERE, log, notify

URL = 'https://www.thechairmangroup.com/index.php?route=catering/booking&btabid=860'
STATE = HERE / 'chairman_state.json'


class BookingPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parts = []
        self.ids = set()
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'section':
            if self.depth or attrs.get('id') == 'booking':
                self.depth += 1
        if self.depth:
            self.ids.add(attrs.get('id', ''))
            if tag in ('script', 'style'):
                self.ignored += 1

    def handle_endtag(self, tag):
        if self.depth and tag in ('script', 'style'):
            self.ignored = max(0, self.ignored - 1)
        if tag == 'section' and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth and not self.ignored:
            self.parts.append(data)


def parse_page(html):
    page = BookingPage()
    page.feed(html)
    text = ' '.join(' '.join(page.parts).split())
    if 'The Chairman Reservation' not in text:
        raise ValueError('Unrecognised booking page (possibly a queue or challenge); state preserved')
    if {'booking-schedule', 'calendar-month', 'available-guests'} <= page.ids:
        return {'status': 'booking_form', 'notice': 'Booking form is open; check available dates and party sizes.'}
    if 'fully booked' in text.lower():
        return {'status': 'fully_booked', 'notice': text}
    raise ValueError('Booking page layout/status is unrecognised; state preserved')


def fetch_page():
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        if urlparse(response.url).hostname not in ('www.thechairmangroup.com', 'thechairmangroup.com'):
            raise ValueError('Booking page redirected to another site; state preserved')
        return response.read().decode('utf-8')


def check():
    current = parse_page(fetch_page())
    previous = json.loads(STATE.read_text()) if STATE.exists() else None
    changed = current != previous
    alert = changed and (current['status'] == 'booking_form' or previous is not None)
    log('The Chairman: ' + current['status'] + (' (changed)' if changed else ' (unchanged)'))
    if alert:
        title = ('The Chairman: check availability' if current['status'] == 'booking_form'
                 else 'The Chairman: booking notice changed')
        notify(title, current['notice'][:350])
        with (HERE / 'ALERTS.md').open('a') as output:
            output.write(f"\n## {datetime.now():%Y-%m-%d %H:%M} {title}\n{URL}\n{current['notice']}\n")
    temp = STATE.with_suffix('.tmp')
    temp.write_text(json.dumps(current, indent=2) + '\n')
    temp.replace(STATE)
    return current


def main():
    try:
        check()
        return 0
    except Exception as exc:
        log(f'The Chairman: ERROR {exc}')
        return 1


if __name__ == '__main__':
    sys.exit(main())

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import watch_chairman as watcher

CLOSED = '<section id="booking"><h1>The Chairman Reservation</h1><div>Fully booked until December.</div></section>'
OPEN = '<section id="booking"><h1>The Chairman Reservation</h1><div id="booking-schedule"><div id="calendar-month"></div><div id="available-guests"></div></div></section>'


class ChairmanTests(unittest.TestCase):
    def test_closed_and_open(self):
        self.assertEqual(watcher.parse_page(CLOSED)['status'], 'fully_booked')
        self.assertEqual(watcher.parse_page(OPEN)['status'], 'booking_form')

    def test_unknown_page_is_error(self):
        for html in ('<h1>Queue</h1>', '<section id="booking">The Chairman Reservation</section>'):
            with self.assertRaises(ValueError):
                watcher.parse_page(html)

    def test_transitions_deduplication_and_failure_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'state.json'
            with patch.multiple(watcher, HERE=root, STATE=state), patch.object(watcher, 'log'), patch.object(watcher, 'notify') as notify, patch.object(watcher, 'fetch_page') as fetch:
                fetch.return_value = CLOSED
                watcher.check()
                notify.assert_not_called()
                fetch.return_value = OPEN
                watcher.check()
                watcher.check()
                self.assertEqual(notify.call_count, 1)
                before = state.read_text()
                fetch.return_value = '<h1>Service unavailable</h1>'
                self.assertEqual(watcher.main(), 1)
                self.assertEqual(state.read_text(), before)
                fetch.return_value = CLOSED
                watcher.check()
                fetch.return_value = OPEN
                watcher.check()
                self.assertEqual(notify.call_count, 3)

    def test_first_run_open_alerts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.multiple(watcher, HERE=root, STATE=root / 'state.json'), patch.object(watcher, 'log'), patch.object(watcher, 'notify') as notify, patch.object(watcher, 'fetch_page', return_value=OPEN):
                watcher.check()
                notify.assert_called_once()


if __name__ == '__main__':
    unittest.main()

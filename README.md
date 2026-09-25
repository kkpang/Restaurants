# Restaurants

Hong Kong restaurant booking links are in [restaurants.md](restaurants.md).

## Availability watchers

- **Wing:** checks SevenRooms for 1–8 guests over the next 60 days and alerts on new bookable slots.
- **The Chairman:** checks its public booking page. Alerts when the booking form appears or the fully-booked notice changes. This is a page-status alert, not confirmation of a specific table. It does not select, hold, or book tables. Exact slots and party sizes must be checked manually. The open-form detector is based on the site's booking script; a live cancellation has not yet been observed.

Run both once with `python3 watch/watch_restaurants.py`, or The Chairman alone with `python3 watch/watch_chairman.py`. macOS notifications and `watch/ALERTS.md` contain alerts. The first fully-booked check establishes a quiet baseline; repeated identical results do not alert. Errors are logged and preserve the previous state.

The launchd template in `watch/com.kenpang.restaurant-watch.plist` runs both hourly from 09:00 through 21:00 in the Mac's local timezone. It uses this Mac's absolute project path; adjust paths and Python executable if moving the project. The template must be installed and loaded separately to enable scheduled checks. The Mac must be awake and connected for timely checks.

Logs, alert history, and deduplication state are local and excluded from Git.

Run tests with `python3 -m unittest discover -s watch -p 'test_*.py'`.

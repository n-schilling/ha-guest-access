# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), the versions
[Semantic Versioning](https://semver.org/).

## [0.1.0] - unreleased

### Added

- Guest profiles with any number of `device_tracker` entities, an approval (once until, permanent until, permanent, optionally any number of time windows), a grace time within which a return continues the visit (and after which a once approval ends), rooms and a time per visit.
- Counting rules: a guest counts while the approval holds and a tracker is home; an expiry while home keeps the guest counting and fires an event; a once approval ends after the grace time; a visit survives a restart when a tracker returns within ten minutes.
- Room lock: lockable rooms are areas with one door contact; while only guests are home, the doors of rooms no counting guest may enter raise a room violation.
- Entities: per guest a presence sensor, a status sensor (counts, time up, approval expired, home without approval, waiting after restart, away), a visit-end timestamp and an event entity; for all guests "Guests home", "Only guests home", "Guests home since" and the room violation event entity.
- A visit log per guest (on by default): date, start and length on a quarter-hour grid, 90 days of single visits and 13 months of totals, shown on the page with a CSV export, and a sensor with the hours of the current month.
- The page shows the version and the deployed commit; `scripts/deploy.sh` writes that commit.
- Approval changes name the administrator: `by` in the event data and the user in the logbook.
- Repair issues for trackers, residents, door contacts and areas that are gone.
- Brand icon.
- An administrator-only page in the sidebar to add, change, lock and delete guests and to set residents and rooms, over administrator-only WebSocket commands.

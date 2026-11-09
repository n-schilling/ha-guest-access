# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), the versions
[Semantic Versioning](https://semver.org/).

## [0.3.0] - unreleased

### Added

- A photo per guest, uploaded on the page as Home Assistant's own images: the counts and status entities show it as `entity_picture`, `guest_list` as `picture`, the page in the list. A replaced or removed photo and the photo of a deleted guest are deleted; an upload that is not saved too.
- A note per guest for administrators, on the page only.
- `save_guest` takes `picture` and `note`; left out, they keep their value.

## [0.2.0] - unreleased

### Added

- The interface is described in the README (section Interface) and pinned by tests: entity and unique IDs, event types and data, attributes, WebSocket commands, store format.
- Names for the data of the guests' events and of the room violation in English and German.
- Quality scale up to Platinum, rule by rule in quality_scale.yaml and checked by the tests.
- README sections Examples, Known limitations, Troubleshooting and Removal; a security policy and issue forms.

### Changed

- Guest names in the attributes of "Guests home" and in the room violation follow a device name given in Home Assistant, as `guest_list` already did.
- `visit_ends` in the events `arrived` and `time_up` is to the second, as the sensor and `guest_list` show it.

## [0.1.0] - 2026-11-09

### Added

- Guest profiles with any number of `device_tracker` entities, an approval (once until, permanent until, permanent, optionally any number of time windows), a grace time within which a return continues the visit (and after which a once approval ends), rooms and a time per visit.
- Counting rules: a guest counts while the approval holds and a tracker is home; an expiry while home keeps the guest counting and fires an event; a once approval ends after the grace time; a visit survives a restart when a tracker returns within ten minutes.
- Room lock: lockable rooms are areas with one door contact; while only guests are home, the doors of rooms no counting guest may enter raise a room violation.
- Entities: per guest a presence sensor, a status sensor (counts, time up, approval expired, home without approval, waiting after restart, away), a visit-end timestamp and an event entity; for all guests "Guests home", "Only guests home", "Guests home since" and the room violation event entity.
- A visit log per guest, off by default: date, start and length on a grid, single visits and monthly totals kept for a set time, shown on the page with a CSV export; a sensor with the hours of the current month, disabled by default.
- Settings for the resume time after a restart and for the grid and keeping of the visit log; any time per visit from 1 to 1440 minutes.
- New guests' entities are named guest_<name>_<entity name>.
- Status `inactive` for a guest without an approval who is not home, so dashboards can leave such guests out.
- Attribute `guest_list` on "Guests home": every guest but inactive ones with name, status, status sensor and visit end, so a dashboard can list the guests as they are.
- Names, rooms, the guest list and administrators in attributes are not recorded in the history.
- Diagnostics with placeholders instead of names, entities and areas.
- License (Apache 2.0) and installation through the Marketplace by link; requires Home Assistant 2026.11; releases from main.
- The page shows the version and the deployed commit; `scripts/deploy.sh` writes that commit.
- Approval changes name the administrator: `by` in the event data and the user in the logbook.
- Repair issues for trackers, residents, door contacts and areas that are gone.
- Brand icon.
- An administrator-only page in the sidebar to add, change, lock and delete guests and to set residents and rooms, over administrator-only WebSocket commands.

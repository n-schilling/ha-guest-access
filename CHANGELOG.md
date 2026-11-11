# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), the versions
[Semantic Versioning](https://semver.org/).

## [0.6.0] - 2026-11-11

### Changed

- The page has two tabs in the header row, next to the integration's icon and name, styled like Network Plus: "Guests" with the guest list and "Add guest", and "Rooms" with the residents, the lockable rooms, the room lock and "Edit". The tab is in the URL (`/guest-access/guests`, `/guest-access/rooms`), so a reload and the browser's back button keep it. At phone width the tabs sit at the bottom of the screen with icons. Guests and the edit of residents and rooms stay subpages with the back arrow; closing one returns to its tab.
- The header shows the integration's own icon (its `brand/icon.png`, served by Home Assistant's brands view) left of the name; on a subpage the back arrow takes its place.

### Fixed

- The page check could hang in CI until the job was cancelled, without saying where. Every wait now has a limit: each check (150 s, with the lines it waited at), each WebSocket reply (30 s; a refused subscription fails at once instead of waiting for an event), closing a browser context or the browser (30 s), stopping Home Assistant, and all checks together (7 min), so a hang is a failed check named in the log and Home Assistant is still stopped.

### Added

- The page check tests the new header: icon loaded (natural width above 0, 24 px, from the brands view), name, tabs in the row of the name on desktop width and at the bottom at phone width, the three controls on the right; the tab kept in the URL across a reload, back to Guests with the browser's back button, the edit of rooms returning to the Rooms tab, and the bottom tabs at phone width. Screenshots refreshed.

## [0.5.0] - 2026-11-11

### Added

- The page has the same header as Nico's other apps and integrations, on the list and on every subpage: "As of HH:MM:SS" for when the page last got its data (hidden at phone width), a refresh button that fetches the data again over the WebSocket without reloading the page (it spins while loading; an open form is redrawn and keeps what was typed), and a settings button to Home Assistant's page of the integration.
- The page check tests the header on the list and every subpage: order, stamp, refresh (subscribes again, spins, moves the stamp on), settings (opens the integration's page without reloading), and the stamp hidden at phone width. Screenshots refreshed.

### Changed

- CI: the Page job uses the runner's Google Chrome instead of installing Playwright's Chromium with packages from the Ubuntu mirrors, which failed with DNS errors.

## [0.4.0] - 2026-11-10

### Added

- The page subscribes again by itself when it was opened while the integration was still loading, for example right after an update; before, it kept showing the error until the browser reloaded.
- A screenshot of the page at phone width in dark mode; the page checks write it with the other README pictures.

### Fixed

- A change of the approval while the guest is away within the grace time, locking included, ends that visit where the guest left. Before, the visit stayed open and a later return logged it as one visit up to that return.
- After a restart, a guest who does not return has left when Home Assistant started, also when the resume time was changed in the meantime.
- The visit log grid counts from local midnight, so a start rounds to full local quarters (or whatever the grid is) in every time zone and with every grid.
- The photo upload refuses an image of more than 40 megapixels before decoding it, decodes a JPEG already scaled down and reads the file outside the event loop; a user who is no administrator gets 403 instead of 401.
- A setup that fails after the start leaves no engine running that would save its state over the next one.
- A state change of a tracker, resident or door that changes nothing shown no longer updates the entities and the page.
- `scripts/deploy.sh` replaces the folder on the host instead of unpacking over it, so removed files do not stay behind.

### Changed

- The store keeps, for a guest waiting to resume after a restart, when Home Assistant started (`restarted` in the runtime state); a store without it reads as before.

## [0.3.1] - 2026-11-10

### Fixed

- The page no longer shows "commit unknown" below the version when installed from a release; the commit appears only for a test deployment with `scripts/deploy.sh`.

## [0.3.0] - 2026-11-10

### Added

- A photo per guest, uploaded on the page through `POST /api/guest_access/picture` (administrators only) into Home Assistant's images: the counts and status entities show it as `entity_picture` (not recorded), `guest_list` as `picture`, the page in the list. Guest Access deletes only its own photos: replaced or removed ones, the photo of a deleted guest, uploads never saved (after a day) and all of them when the integration is removed. A photo is stored encoded anew: without metadata, at most 1024 pixels wide and high, under a fixed file name. A photo deleted elsewhere leaves the guest without one.
- A note per guest for administrators, on the page only.
- `save_guest` takes `picture` and `note`; left out, they keep their value.
- A new or changed name has at most 100 characters.
- The interface is described in the README (section Interface) and pinned by tests: entity and unique IDs, event types and data, attributes, WebSocket commands, the photo upload, store format.
- Names for the data of the guests' events and of the room violation in English and German.
- Quality scale up to Platinum, rule by rule in quality_scale.yaml and checked by the tests.
- README sections Examples, Known limitations, Troubleshooting and Removal; a security policy and issue forms.

### Changed

- Guest names in the attributes of "Guests home" and in the room violation follow a device name given in Home Assistant, as `guest_list` already did, and at once, not only with the next change.
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

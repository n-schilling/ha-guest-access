# Guest Access

[![Marketplace: custom](https://img.shields.io/badge/Marketplace-custom-41BDF5.svg)](#installation)

A Home Assistant integration to manage guests without making them persons in Home Assistant. Each guest has a profile: any number of trackers, an approval with a validity and optional time windows, the rooms the guest may enter, the time per visit and, if wanted, a visit log. Guest Access tells Home Assistant which guests count as home, whether only guests are home and what happens to each guest; your automations decide what follows, from greeting a guest with light to an alarm system that treats approved guests like residents.

Guests are managed on a page in the sidebar, for administrators only. No entity can change an approval.

## Screenshots

The guests with their state and approval, made up for these pictures:

<img src="docs/screenshots/guests.png" alt="List of guests: two count as home, one is locked, two are away" width="700">

A guest with a key tag as tracker and two weekly time windows:

<img src="docs/screenshots/guest.png" alt="Form of a guest: name, trackers, approval, grace time and time windows" width="700">

The visit log of a guest, on a 15-minute grid, with monthly totals and a CSV export:

<img src="docs/screenshots/visit-log.png" alt="Visit log: running visit, totals of this and last month, single visits" width="700">

## Design

### Overview

```mermaid
flowchart LR
    admin(["Administrator"]) -->|"page, admin only"| ws["WebSocket commands"]
    subgraph ha["Home Assistant"]
        trackers["device_tracker<br/>of any integration"]
        persons["person<br/>residents"]
        doors["binary_sensor<br/>door contacts"]
        areas["areas<br/>lockable rooms"]
    end
    subgraph ga["Guest Access"]
        ws --> engine["Engine<br/>rules, deadlines, room lock"]
        store[("Store<br/>profiles and runtime state")] <--> engine
    end
    trackers --> engine
    persons --> engine
    doors --> engine
    areas --> engine
    engine --> entities["Entities<br/>per guest and summary"]
    engine --> repairs["Repair issues"]
    entities --> automations["Your automations"]
    automations --> comfort["Light, media, climate"]
    automations --> notify["Notifications"]
    automations --> security["Alarm system, room lock"]
```

Guest Access reads trackers, residents and door contacts and decides; everything to the right of the entities is up to your automations, not part of the integration.

### Guests

A guest is a profile with:

| Field | Meaning |
|---|---|
| Name | shown on the page and in events |
| Trackers | one or more `device_tracker` entities of any integration (a Bluetooth beacon, a phone on Wi-Fi); the guest is home when one of them is `home`; `unknown` and `unavailable` never count |
| Approval | `off`, `once until <datetime>`, `permanent until <datetime>`, `permanent` |
| Time windows | optional for permanent approvals (with or without an end): any number of windows, each weekdays and a time range; the approval applies within any of them, e.g. Mon–Fri 08:00–18:00 and Sat 10:00–14:00 |
| Grace time | how long all trackers may be away and the visit still goes on when one returns; for a once approval also when it ends (default 15 min) |
| Rooms | the lockable rooms (see Room lock) the guest may enter on top of the unlockable ones, or everything |
| Time per visit | 1 to 1440 minutes (default 60) or unlimited, counted from the arrival that starts the visit |
| Visit log | off by default; see Visit log |

### When a guest counts

A guest counts while all of these hold:

1. the approval is not `off` and its end, if any, has not passed,
2. the time window, if any, contains the current time,
3. one of the guest's trackers is `home`.

When no tracker is home any more, the guest stops counting at once (`left`). A return within the grace time continues the same visit: its end stays, no new `arrived` is raised. A return later is a new visit with a new end. Locking the guest or an approval that is no longer valid ends the visit as well.

A `once` approval is one visit: when no tracker of the guest has been home for the grace time, the approval switches to `off`. A guest who returns later needs a new approval.

The status sensor of a guest follows these rules:

```mermaid
stateDiagram-v2
    [*] --> away
    away --> counting: tracker home, approval valid
    away --> not_approved: tracker home, approval not valid
    not_approved --> counting: approval becomes valid
    counting --> time_up: visit time over
    counting --> approval_expired: end passed or window closed
    time_up --> approval_expired: end passed or window closed
    counting --> away: all trackers away (left)
    time_up --> away: all trackers away (left)
    approval_expired --> away: all trackers away (left)
    counting --> not_approved: locked on the page
    time_up --> not_approved: locked on the page
    approval_expired --> not_approved: locked on the page
    not_approved --> inactive: all trackers away
    away --> inactive: approval locked or ended
    inactive --> away: approved again
    inactive --> not_approved: tracker home
    counting --> resuming: Home Assistant restarts
    resuming --> counting: tracker home within the resume time
    resuming --> away: no tracker home in the resume time
```

`away` is an approved guest who is not home, including the grace time: the guest does not count, but a return within it continues the visit. `inactive` is a guest without an approval (locked, or its end has passed) who is not home. A visit with a `once` approval, step by step:

```mermaid
sequenceDiagram
    actor Admin
    participant T as Trackers
    participant GA as Guest Access
    participant A as Automations
    Admin->>GA: approval once until Sunday 18:00
    GA-->>A: approval_changed (reason changed, by Admin)
    T->>GA: phone home
    GA-->>A: arrived, counts on, visit ends at +60 min
    T->>GA: phone away (taking out the rubbish)
    GA-->>A: left, counts off
    T->>GA: phone home again after 5 min
    Note over GA: within the grace time:<br/>same visit, same end, no arrived
    GA-->>A: counts on
    Note over GA: visit time over while home
    GA-->>A: time_up, guest keeps counting
    T->>GA: phone away
    GA-->>A: left, counts off
    Note over GA: grace time over
    GA-->>A: approval_changed (reason visit_over), approval off
```

### Several guests

If only guests are home, their rooms add up, because an opened door cannot be told apart by guest: the free rooms are the union of the rooms of all guests who count. Time is per guest.

### Expiry while the guest is home

When the visit time of a guest runs out, or the approval ends (its end passes or its time window closes) while the guest is home, the guest keeps counting until they leave or are locked, and the guest's event entity fires `time_up` or `approval_expired`.

### Room lock

Rooms are configured once on the entry: each lockable room is a Home Assistant area with exactly one door contact (`binary_sensor`), so names follow the area registry. A room that stops being lockable is removed from every guest. The lock starts when guests count and no resident is home, given as a list of `person` entities on the entry. A room is locked while its door is closed, and an opening is a change to open from the last known real state closed (a door opened while its contact was unavailable counts once the contact reports; a contact that returns to a door already open before does not); guests waiting to resume after a restart keep their rooms free unless they were locked; a room whose door is open when the lock starts stays free for that visit. The lock ends when a resident comes home or no guest counts any more.

```mermaid
flowchart TD
    change["tracker, resident or door changes"] --> counts{"a guest counts?<br/>a guest resuming after a restart<br/>keeps a running lock"}
    counts -->|no| off["no lock"]
    counts -->|yes| resident{"a resident<br/>home?"}
    resident -->|yes| off
    resident -->|no| start["lock active<br/>doors open now stay free"]
    start --> door{"a door opens<br/>closed to open"}
    door --> free{"room free?<br/>open at lock start, or in the rooms<br/>of a guest who counts or resumes"}
    free -->|yes| nothing["nothing happens"]
    free -->|no| violation["Room violation: opened<br/>area, door, guests"]
```

### What Home Assistant gets

Each guest is a device with its entities.

| Kind | Entity | Purpose |
|---|---|---|
| Per guest | `binary_sensor` "<guest> counts" (presence) | automations, the guest's state on dashboards |
| Per guest | `sensor` "<guest> status" (enum: `counting`, `time_up`, `approval_expired`, `not_approved`, `resuming`, `away`, `inactive`) | dashboards show it as it is, no template; `inactive` (no approval and not home) lets them leave such guests out |
| Per guest | `sensor` "<guest> visit ends" (timestamp; unknown while the guest does not count or the time is unlimited) | dashboards, time triggers |
| Per guest | `sensor` "<guest> hours this month" (hours of the finished visits this month from the visit log; unknown without a log; disabled by default, see Privacy) | the hours on a dashboard |
| Per guest | `event` "<guest>" with the types `arrived`, `left`, `time_up`, `approval_expired`, `approval_changed` (with `reason` `changed` or `visit_over`, and `by`: the administrator who changed it; the logbook names that user too) | push and log stay in automations |
| Only guests | `binary_sensor` "Only guests home" (on while guests count and no resident is home) | anything that should behave differently when guests are alone |
| Summary | `binary_sensor` "Guests home" (presence) with attributes: guests who count, free rooms, locked rooms, and `guest_list` (every guest but inactive ones, by name: `name`, `status`, `status_entity`, `visit_ends` while the guest counts with time left or time up) | the one entity automations read to treat guests as home; `guest_list` lets a dashboard list the guests without searching the entity registry |
| Summary | `sensor` "Guests home since" (timestamp: the earliest arrival of the guests who count; unknown while none counts; a restart or a return within the grace time does not move it) | dashboards showing since when guests are home |
| Room lock | `event` "Room violation" with the type `opened`, carrying the area, the door and the guests who count | push, log and image series stay in automations |

A new guest's entities get the IDs `guest_<name>_<entity name>`, in the language of Home Assistant, so a guest's entities stand together; renaming a guest later keeps the IDs.

The integration only provides state and triggers; it notifies nobody and switches nothing. Every reaction (turning on lights on arrival, keeping the TV off while only guests are home, an alarm system that counts approved guests as home) is an automation that uses state triggers on these entities. No template is needed for that.

No entity changes an approval: Home Assistant cannot limit an entity to administrators, so approvals are changed only on the page.

### Visit log

For guests whose hours matter (a cleaner, a babysitter) Guest Access can keep a visit log, not a surveillance record. It is off by default and switched on per guest; switched off, the log kept so far is deleted. Each finished visit is logged with its date, start and length, both on a grid (default 15 minutes); a return within the grace time is the same visit. Rooms, doors, places and overruns are not logged. Single visits are kept for 90 days and monthly totals (visits, hours) for 13 months by default. The log shows only on the page, with a CSV export and a delete button; the sensor "<guest> hours this month" carries the hours of the finished visits this month.

### Settings

On the page, under residents and rooms:

| Setting | Default | Meaning |
|---|---|---|
| Residents | none | `person` entities; the room lock applies while none of them is home |
| Lockable rooms | none | areas, each with exactly one door contact |
| Resume time | 10 min | after a restart, how long a guest who counted may take to be seen again and continue the visit |
| Grid of the visit log | 15 min | start and length of a logged visit are rounded to it |
| Keep single visits | 90 days | then a visit is deleted, its monthly total stays |
| Keep monthly totals | 13 months | then the total is deleted |

### Privacy

Guest Access stores only the profiles, the visit in progress and, for guests with a visit log, the rounded visits. It writes no guest names to the Home Assistant log.

- The names, rooms, guest list and administrator in the attributes of "Guests home", the room violation and the guests' events are not recorded in the history.
- The sensor "<guest> hours this month" is disabled when it is created: every user can read an entity, while the visit log is meant for administrators. Enable it where you need the hours.
- Home Assistant still records the state of each guest's entities (counts, status, events) to the minute for as long as your recorder keeps history. If the history should not hold more than the visit log, exclude the guests' entities from the recorder, for example:

  ```yaml
  recorder:
    exclude:
      entity_globs:
        - binary_sensor.guest_*_counts
        - sensor.guest_*_status
        - sensor.guest_*_visit_ends
        - event.guest_*_activity
  ```

  The endings follow the language of Home Assistant (in German `_zahlt`, `_status`, `_besuchsende`, `_aktivitat`). The summary entities (`guest_access_*`) stay recorded, for automations or dashboards that use their history. Exclude the trackers of guests too if their integration records more than home or away, for example a room.

### Diagnostics

**Settings → Devices & services → Guest Access → ⋮ → Download diagnostics** gives the settings, every guest with status, approval, rooms and visit state, the state of each tracker, resident and door, and the open repair kinds. Names, entity IDs and areas are replaced by placeholders (Guest 1, Room 1), times by minutes from now and the visit log by its size, so the file can be attached to an issue as it is.

### Repairs

Once Home Assistant has started, Guest Access opens a repair issue for every tracker, resident or door contact that is neither registered nor has a state, and for every lockable room whose area is gone; doors and areas as errors, because the room lock cannot see them. An issue closes by itself when the entity or area is back or no longer used.

### Page

A sidebar page for administrators only: the list of guests with their state, a form per guest, a "lock now" button that sets the approval to `off`, the residents, rooms and timings, and at the bottom the version and the commit it was deployed from. Non-administrators get no page.

### State

Profiles and the runtime state (approval, last time a tracker was home, deadlines, lock) live in the integration's store, so a restart neither loses nor extends anything. After a restart a guest counts again only once a tracker reports `home`; when that happens within the resume time, the visit goes on with its end and without a new `arrived`, otherwise the guest has left.

## Installation

1. **Settings → Marketplace → Add from link** (top right), enter `https://github.com/n-schilling/ha-guest-access` as GitHub link and add it. Adding a repository by link asks you to connect GitHub once.
2. Install **Guest Access** in the Marketplace and restart Home Assistant.
3. **Settings → Devices & services → Add integration → Guest Access.**
4. Open **Guest Access** in the sidebar, set residents and rooms, and add the first guest.

Requires Home Assistant 2026.11 or later. Without the Marketplace, copy `custom_components/guest_access` into the `custom_components` folder of your configuration directory and restart. There are no requirements outside Home Assistant.

## Development

```bash
uv venv --python 3.14 && uv pip install -r requirements_test.txt
scripts/check.sh
```

`scripts/check.sh` runs what CI runs: ruff, the changelog and translation checks, mypy, the tests with their coverage threshold, the page checks and hassfest in Docker.

The page checks start a throwaway Home Assistant with made-up guests, reachable from this machine only, drive the page in a headless browser (list, form, visit log, lock, rename, errors, phone width, dark mode, no page for non-administrators) and stop Home Assistant again. They need their own environment:

```bash
uv venv --python 3.14 .venv-panel && uv pip install --python .venv-panel/bin/python -r requirements_panel.txt
```

They use an installed Google Chrome, otherwise Playwright's Chromium (`.venv-panel/bin/python -m playwright install chromium`). The pictures in this README come from the same run:

```bash
.venv-panel/bin/python -I scripts/panel/check_panel.py --screenshots docs/screenshots
```

Releases: CI on `main` tags the version from `manifest.json` and publishes a GitHub release with its CHANGELOG section; the Marketplace offers it as an update.

For testing on a Home Assistant OS host before a release (copies the files, writes the deployed commit for the page and restarts Home Assistant):

```bash
scripts/deploy.sh <ssh-host>
```

The page shows the version and that commit at the bottom; `-dirty` marks files that differ from it.

## License

Apache License 2.0, see [LICENSE](LICENSE).

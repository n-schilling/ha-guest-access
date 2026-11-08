# Guest Access

A Home Assistant integration that decides which guests count as present for an alarm system: one profile per guest with any number of trackers, an approval with a validity, optionally a time window, the rooms the guest may enter and the time per visit.



Status: 0.1.0 in development, not deployed yet.

## Design

### Guests

A guest is a profile with:

| Field | Meaning |
|---|---|
| Name | shown on the page and in events |
| Trackers | one or more `device_tracker` entities of any integration (a Bluetooth beacon, a phone on Wi-Fi); the guest is home when one of them is `home`; `unknown` and `unavailable` never count |
| Approval | `off`, `once until <datetime>`, `permanent until <datetime>`, `permanent` |
| Time window | optional for permanent approvals: weekdays and a time range in which the approval applies |
| Grace time | once approvals only: how long all trackers may be away before the approval ends (default 15 min) |
| Rooms | the lockable rooms (see Room lock) the guest may enter on top of the unlockable ones, or everything |
| Time per visit | 30, 60 (default) or 120 minutes or unlimited, counted from each arrival |

### When a guest counts

A guest counts while all of these hold:

1. the approval is not `off` and its end, if any, has not passed,
2. the time window, if any, contains the current time,
3. one of the guest's trackers is `home`.

A `once` approval is one visit: when no tracker of the guest has been home for the grace time, the approval switches to `off`. A guest who returns later needs a new approval.

### Several guests

If only guests are home, their rooms add up, because an opened door cannot be told apart by guest: the free rooms are the union of the rooms of all guests who count. Time is per guest.

### Expiry while the guest is home

When the visit time of a guest runs out, or the approval ends (its end passes or its time window closes) while the guest is home, the guest keeps counting until they leave or are locked, and the guest's event entity fires `time_up` or `approval_expired`.

### Room lock

Rooms are configured once on the entry: each lockable room is a Home Assistant area with exactly one door contact (`binary_sensor`), so names follow the area registry. A room that stops being lockable is removed from every guest. The lock starts when guests count and no resident is home, given as a list of `person` entities on the entry. A room is locked while its door is closed, and only a change from closed to open is an opening (a contact that returns from unavailable while the door is open is not); guests waiting to resume after a restart keep their rooms free; a room whose door is open when the lock starts stays free for that visit. The lock ends when a resident comes home or no guest counts any more.

### What Home Assistant gets

| Kind | Entity or event | Purpose |
|---|---|---|
Each guest is a device with its entities.

| Kind | Entity | Purpose |
|---|---|---|
| Per guest | `binary_sensor` "<guest> counts" (presence) | automations, the guest's state on dashboards |
| Per guest | `sensor` "<guest> status" (enum: `counting`, `time_up`, `approval_expired`, `not_approved`, `resuming`, `away`) | dashboards show it as it is, no template |
| Per guest | `sensor` "<guest> visit ends" (timestamp; unknown while the guest does not count or the time is unlimited) | dashboards, time triggers |
| Per guest | `event` "<guest>" with the types `arrived`, `left`, `time_up`, `approval_expired`, `approval_changed` | push and log stay in automations |
| Only guests | `binary_sensor` "Only guests home" (on while guests count and no resident is home) | anything that should behave differently when guests are alone |
| Summary | `binary_sensor` "Guests home" (presence) with attributes: guests who count, free rooms, locked rooms | alarm automations read only this |
| Room lock | `event` "Room violation" with the type `opened`, carrying the area, the door and the guests who count | push, log and image series stay in automations |

The integration only provides state and triggers; it notifies nobody, switches nothing and never arms or disarms. Every reaction, inside the alarm system or elsewhere (keeping the TV off while only guests are home, opening blinds or turning on lights on arrival), is an automation that uses state triggers on these entities. No template is needed for that.

No entity changes an approval: Home Assistant cannot limit an entity to administrators, so approvals are changed only on the page.

### Page

A sidebar page for administrators only: the list of guests with their state, a form per guest, a "lock now" button that sets the approval to `off`, and the rooms of the entry. Non-administrators get no page.

### State

Profiles and the runtime state (approval, last time a tracker was home, deadlines, lock) live in the integration's store, so a restart neither loses nor extends anything. After a restart a guest counts again only once a tracker reports `home`; when that happens within ten minutes, the visit goes on with its end and without a new `arrived`, otherwise the guest has left.

## Development

```bash
uv venv --python 3.14 && uv pip install -r requirements_test.txt
scripts/check.sh
```

`scripts/check.sh` runs what CI runs: ruff, the changelog and translation checks, mypy, the tests with their coverage threshold, and hassfest in Docker.

Deploy to a Home Assistant OS host:

```bash
tar -C custom_components --exclude __pycache__ -cf - guest_access | ssh <host> 'tar -C /mnt/data/supervisor/homeassistant/custom_components -xf -'
```

then delete the `._*` files macOS adds and restart Home Assistant.

# Guest Access

A Home Assistant integration that decides which guests count as present for an alarm system: one profile per guest with any number of trackers, an approval with a validity, optionally a time window, the rooms the guest may enter and the time per visit.



Status: scaffold. The entry loads and unloads; everything under Design is still to be built.

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
| Rooms | the living area always; bedroom and children's room each on top, or everything |
| Time per visit | 30, 60 (default) or 120 minutes or unlimited, counted from each arrival |

### When a guest counts

A guest counts while all of these hold:

1. the approval is not `off` and its end, if any, has not passed,
2. the time window, if any, contains the current time,
3. one of the guest's trackers is `home`.

A `once` approval is one visit: when no tracker of the guest has been home for the grace time, the approval switches to `off`. A guest who returns later needs a new approval.

### Several guests

If only guests are home, their rights add up, because an opened door cannot be told apart by guest: the free rooms are the union of the rooms of all guests who count.

Open (proposals, not decided): the visit time ends with the latest deadline of the guests who count; an approval that ends while the guest is home keeps the guest counting until they leave, and raises the same event as an expired visit time.

### Room lock

Rooms are configured once on the entry: name and the door contact (`binary_sensor`) of each lockable room. The lock starts when guests count and no resident is home, given as a list of `person` entities on the entry. A room is locked while its door is closed; a room whose door is open when the lock starts stays free for that visit. The lock ends when a resident comes home or no guest counts any more.

### What Home Assistant gets

| Kind | Entity or event | Purpose |
|---|---|---|
| Per guest | `binary_sensor` "<guest> counts" (presence) | automations, the guest's state on dashboards |
| Summary | `binary_sensor` "Guests home" (presence) with attributes: guests who count, free rooms, locked rooms, earliest deadline | alarm automations read only this |
| Events | `guest_access_arrived`, `guest_access_left`, `guest_access_room_violation`, `guest_access_time_up`, `guest_access_approval_changed` | push, log and image series stay in automations |

The integration notifies nobody and never arms or disarms anything. Reactions stay in the alarm system's automations.

### Page

A sidebar page for administrators only: the list of guests with their state, a form per guest, a "lock now" button that sets the approval to `off`, and the rooms of the entry. Non-administrators get no page.

### State

Profiles and the runtime state (approval, last time a tracker was home, deadlines, lock) live in the integration's store, so a restart neither loses nor extends anything. After a restart a guest counts again only once a tracker reports `home`.

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

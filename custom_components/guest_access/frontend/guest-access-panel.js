// Guest Access panel: the page in the sidebar where administrators add guests,
// approve and lock them, and set the residents, the lockable rooms and the
// timings. Every change goes to the integration over the WebSocket API; the
// page follows the integration's state live.
//
// The page is built as STANDARD.md §7 describes it (reference: BLE Floorplan):
// Home Assistant's frame for pages with tabs (hass-tabs-subpage) with the two
// areas Guests and Setup as tabs in the header, at the bottom on a narrow
// screen; the pages of an area as Home Assistant's tabs (ha-tab-group) below
// it. A guest opens as a subpage (?key=<guest>, a new one ?key=new) with a back
// arrow, its name in the header and its views as tabs (&view=). At the end of
// the header: the stamp, refresh and the button to Home Assistant's page of the
// integration. Settings are Home Assistant's settings rows with one save button
// that shows only while something differs. Explanations sit behind an (i),
// errors read one line by their kind, numbers follow the number format of the
// user's profile. Colours, fonts and spacing only through Home Assistant's variables.

const DOMAIN = "guest_access";
const PANEL_PATH = "/guest-access";
// Home Assistant's own page of the integration, behind the button at the end of the header
const INTEGRATION_PATH = `/config/integrations/integration/${DOMAIN}`;

if (!customElements.get("guest-access-panel")) {
  const MDI = {
    // mdi:refresh
    refresh: "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z",
    // mdi:cog-outline
    integration: "M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8M12,10A2,2 0 0,0 10,12A2,2 0 0,0 12,14A2,2 0 0,0 14,12A2,2 0 0,0 12,10M10,22C9.75,22 9.54,21.82 9.5,21.58L9.13,18.93C8.5,18.68 7.96,18.34 7.44,17.94L4.95,18.95C4.73,19.03 4.46,18.95 4.34,18.73L2.34,15.27C2.21,15.05 2.27,14.78 2.46,14.63L4.57,12.97L4.5,12L4.57,11L2.46,9.37C2.27,9.22 2.21,8.95 2.34,8.73L4.34,5.27C4.46,5.05 4.73,4.96 4.95,5.05L7.44,6.05C7.96,5.66 8.5,5.32 9.13,5.07L9.5,2.42C9.54,2.18 9.75,2 10,2H14C14.25,2 14.46,2.18 14.5,2.42L14.87,5.07C15.5,5.32 16.04,5.66 16.56,6.05L19.05,5.05C19.27,4.96 19.54,5.05 19.66,5.27L21.66,8.73C21.79,8.95 21.73,9.22 21.54,9.37L19.43,11L19.5,12L19.43,13L21.54,14.63C21.73,14.78 21.79,15.05 21.66,15.27L19.66,18.73C19.54,18.95 19.27,19.04 19.05,18.95L16.56,17.95C16.04,18.34 15.5,18.68 14.87,18.93L14.5,21.58C14.46,21.82 14.25,22 14,22H10M11.25,4L10.88,6.61C9.68,6.86 8.62,7.5 7.85,8.39L5.44,7.35L4.69,8.65L6.8,10.2C6.4,11.37 6.4,12.64 6.8,13.8L4.68,15.36L5.43,16.66L7.86,15.62C8.63,16.5 9.68,17.14 10.87,17.38L11.24,20H12.76L13.13,17.39C14.32,17.14 15.37,16.5 16.14,15.62L18.57,16.66L19.32,15.36L17.2,13.81C17.6,12.64 17.6,11.37 17.2,10.2L19.31,8.65L18.56,7.35L16.15,8.39C15.38,7.5 14.32,6.86 13.12,6.62L12.75,4H11.25Z",
    // mdi:information-outline
    info: "M11,9H13V7H11M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M11,17H13V11H11V17Z",
    // mdi:account-multiple
    guests: "M16 17V19H2V17S2 13 9 13 16 17 16 17M12.5 7.5A3.5 3.5 0 1 0 9 11A3.5 3.5 0 0 0 12.5 7.5M15.94 13A5.32 5.32 0 0 1 18 17V19H22V17S22 13.37 15.94 13M15 4A3.39 3.39 0 0 0 13.07 4.59A5 5 0 0 1 13.07 10.41A3.39 3.39 0 0 0 15 11A3.5 3.5 0 0 0 15 4Z",
    // mdi:tune-variant
    setup: "M8 13C6.14 13 4.59 14.28 4.14 16H2V18H4.14C4.59 19.72 6.14 21 8 21S11.41 19.72 11.86 18H22V16H11.86C11.41 14.28 9.86 13 8 13M8 19C6.9 19 6 18.1 6 17C6 15.9 6.9 15 8 15S10 15.9 10 17C10 18.1 9.1 19 8 19M19.86 6C19.41 4.28 17.86 3 16 3S12.59 4.28 12.14 6H2V8H12.14C12.59 9.72 14.14 11 16 11S19.41 9.72 19.86 8H22V6H19.86M16 9C14.9 9 14 8.1 14 7C14 5.9 14.9 5 16 5S18 5.9 18 7C18 8.1 17.1 9 16 9Z",
    // mdi:chevron-right
    chevron: "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
    // mdi:lock-outline
    lock: "M12,17C10.89,17 10,16.1 10,15C10,13.89 10.89,13 12,13A2,2 0 0,1 14,15A2,2 0 0,1 12,17M18,20V10H6V20H18M18,8A2,2 0 0,1 20,10V20A2,2 0 0,1 18,22H6C4.89,22 4,21.1 4,20V10C4,8.89 4.89,8 6,8H7V6A5,5 0 0,1 12,1A5,5 0 0,1 17,6V8H18M12,3A3,3 0 0,0 9,6V8H15V6A3,3 0 0,0 12,3Z",
    // mdi:delete-outline
    delete: "M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z",
    // mdi:content-save
    save: "M15,9H5V5H15M12,19A3,3 0 0,1 9,16A3,3 0 0,1 12,13A3,3 0 0,1 15,16A3,3 0 0,1 12,19M17,3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V7L17,3Z",
    // mdi:check
    check: "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
    // mdi:plus
    plus: "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",
    // mdi:image-plus
    photo: "M18 15V18H15V20H18V23H20V20H23V18H20V15H18M13.3 21H5C3.9 21 3 20.1 3 19V5C3 3.9 3.9 3 5 3H19C20.1 3 21 3.9 21 5V13.3C20.4 13.1 19.7 13 19 13C17.9 13 16.8 13.3 15.9 13.9L14.5 12L11 16.5L8.5 13.5L5 18H13.1C13 18.3 13 18.7 13 19C13 19.7 13.1 20.4 13.3 21Z",
    // mdi:download
    download: "M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z",
    // mdi:account
    account: "M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z",
    // mdi:account-check
    counting: "M21.1,12.5L22.5,13.91L15.97,20.5L12.5,17L13.9,15.59L15.97,17.67L21.1,12.5M10,17L13,20H3V18C3,15.79 6.58,14 11,14L12.89,14.11L10,17M11,4A4,4 0 0,1 15,8A4,4 0 0,1 11,12A4,4 0 0,1 7,8A4,4 0 0,1 11,4Z",
    // mdi:account-clock
    time_up: "M10.63,14.1C12.23,10.58 16.38,9.03 19.9,10.63C23.42,12.23 24.97,16.38 23.37,19.9C22.24,22.4 19.75,24 17,24C14.3,24 11.83,22.44 10.67,20H1V18C1.06,16.86 1.84,15.93 3.34,15.18C4.84,14.43 6.72,14.04 9,14C9.57,14 10.11,14.05 10.63,14.1V14.1M9,4C10.12,4.03 11.06,4.42 11.81,5.17C12.56,5.92 12.93,6.86 12.93,8C12.93,9.14 12.56,10.08 11.81,10.83C11.06,11.58 10.12,11.95 9,11.95C7.88,11.95 6.94,11.58 6.19,10.83C5.44,10.08 5.07,9.14 5.07,8C5.07,6.86 5.44,5.92 6.19,5.17C6.94,4.42 7.88,4.03 9,4M17,22A5,5 0 0,0 22,17A5,5 0 0,0 17,12A5,5 0 0,0 12,17A5,5 0 0,0 17,22M16,14H17.5V16.82L19.94,18.23L19.19,19.53L16,17.69V14Z",
    // mdi:account-alert
    approval_expired: "M10 4A4 4 0 0 1 14 8A4 4 0 0 1 10 12A4 4 0 0 1 6 8A4 4 0 0 1 10 4M10 14C14.42 14 18 15.79 18 18V20H2V18C2 15.79 5.58 14 10 14M20 12V7H22V13H20M20 17V15H22V17H20Z",
    // mdi:account-cancel
    not_approved: "M10 4A4 4 0 0 0 6 8A4 4 0 0 0 10 12A4 4 0 0 0 14 8A4 4 0 0 0 10 4M17.5 13C15 13 13 15 13 17.5C13 20 15 22 17.5 22C20 22 22 20 22 17.5C22 15 20 13 17.5 13M10 14C5.58 14 2 15.79 2 18V20H11.5A6.5 6.5 0 0 1 11 17.5A6.5 6.5 0 0 1 11.95 14.14C11.32 14.06 10.68 14 10 14M17.5 14.5C19.16 14.5 20.5 15.84 20.5 17.5C20.5 18.06 20.35 18.58 20.08 19L16 14.92C16.42 14.65 16.94 14.5 17.5 14.5M14.92 16L19 20.08C18.58 20.35 18.06 20.5 17.5 20.5C15.84 20.5 14.5 19.16 14.5 17.5C14.5 16.94 14.65 16.42 14.92 16Z",
    // mdi:account-sync
    resuming: "M11 4C8.8 4 7 5.8 7 8S8.8 12 11 12 15 10.2 15 8 13.2 4 11 4M11 14C6.6 14 3 15.8 3 18V20H12.5C12.2 19.2 12 18.4 12 17.5C12 16.3 12.3 15.2 12.9 14.1C12.3 14.1 11.7 14 11 14M18 20C16.6 20 15.5 18.9 15.5 17.5C15.5 17.1 15.6 16.7 15.8 16.4L14.7 15.3C14.3 15.9 14 16.7 14 17.5C14 19.7 15.8 21.5 18 21.5V23L20.2 20.8L18 18.5V20M18 13.5V12L15.8 14.2L18 16.4V15C19.4 15 20.5 16.1 20.5 17.5C20.5 17.9 20.4 18.3 20.2 18.6L21.3 19.7C21.7 19.1 22 18.3 22 17.5C22 15.3 20.2 13.5 18 13.5Z",
    // mdi:account-outline
    away: "M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,6A2,2 0 0,0 10,8A2,2 0 0,0 12,10A2,2 0 0,0 14,8A2,2 0 0,0 12,6M12,13C14.67,13 20,14.33 20,17V20H4V17C4,14.33 9.33,13 12,13M12,14.9C9.03,14.9 5.9,16.36 5.9,17V18.1H18.1V17C18.1,16.36 14.97,14.9 12,14.9Z",
    // mdi:account-lock-outline
    inactive: "M10 12C12.21 12 14 10.21 14 8S12.21 4 10 4 6 5.79 6 8 7.79 12 10 12M10 6C11.11 6 12 6.9 12 8S11.11 10 10 10 8 9.11 8 8 8.9 6 10 6M12 20H2V17C2 14.33 7.33 13 10 13C11 13 12.38 13.19 13.71 13.56C13.41 14.12 13.23 14.74 13.21 15.39C12.23 15.1 11.11 14.9 10 14.9C7.03 14.9 3.9 16.36 3.9 17V18.1H12C12 18.13 12 18.17 12 18.2V20M20.8 17V15.5C20.8 14.1 19.4 13 18 13C16.6 13 15.2 14.1 15.2 15.5V17C14.6 17 14 17.6 14 18.2V21.7C14 22.4 14.6 23 15.2 23H20.7C21.4 23 22 22.4 22 21.8V18.3C22 17.6 21.4 17 20.8 17M19.5 17H16.5V15.5C16.5 14.7 17.2 14.2 18 14.2C18.8 14.2 19.5 14.7 19.5 15.5V17Z",
  };

  // The areas of the page and their pages: area, icon, text, pages (page, text)
  const AREAS = [
    ["guests", "guests", "tabGuests", [["list", "pageList"]]],
    ["setup", "setup", "tabSetup", [["overview", "pageOverview"], ["residents", "pageResidents"], ["rooms", "pageRooms"], ["timings", "pageTimings"]]],
  ];
  // The addresses of before the areas, as bookmarks still have them; /guests is the area now
  const OLD_PAGES = { rooms: "setup/rooms" };
  const areaOf = (page) => AREAS.find((a) => a[3].some(([p]) => p === page)) || AREAS[0];
  const pagePath = (page) => `${PANEL_PATH}/${areaOf(page)[0]}/${page}`;
  // The views of a guest: view, text
  const GUEST_VIEWS = [["details", "viewDetails"], ["approval", "viewApproval"], ["rooms", "viewRooms"], ["log", "viewLog"]];
  const KINDS = ["off", "once", "until", "permanent"];
  // A failed subscription, the entry still loading say, is tried again after this time
  const RETRY_MS = 5000;
  // Colour per status, as the status sensor shows it; the status is also written out
  const STATUS_COLOR = {
    counting: "var(--success-color, #43a047)",
    time_up: "var(--warning-color, #ffa600)",
    approval_expired: "var(--warning-color, #ffa600)",
    not_approved: "var(--warning-color, #ffa600)",
    resuming: "var(--info-color, #039be5)",
    away: "var(--secondary-text-color, #727272)",
    inactive: "var(--disabled-text-color, #9e9e9e)",
  };
  // The HTTP answers of the photo upload, as the kinds of error of the WebSocket
  const HTTP_CODES = { 400: "invalid_format", 403: "unauthorized", 404: "not_loaded" };

  const TEXTS = {
    en: {
      title: "Guest Access",
      tabGuests: "Guests",
      tabSetup: "Setup",
      pageList: "Guests",
      pageOverview: "Overview",
      pageResidents: "Residents",
      pageRooms: "Rooms",
      pageTimings: "Timings",
      viewDetails: "Guest",
      viewApproval: "Approval",
      viewRooms: "Rooms and time",
      viewLog: "Visit log",
      guests: "Guests",
      addGuest: "Add guest",
      newGuest: "New guest",
      noGuests: "No guests yet.",
      noGuestsHelp: "A guest counts as home only with an approval.",
      lock: "Lock",
      lockConfirm: "Lock {name}? The guest no longer counts as home until approved again.",
      delete: "Delete",
      deleteGuest: "Delete guest",
      deleteConfirm: "Delete {name} with the device and its entities?",
      cancel: "Cancel",
      save: "Save",
      field_name: "Name",
      field_trackers: "Trackers",
      field_kind: "Approval",
      field_until: "Until",
      field_grace: "Grace time",
      field_all_rooms: "All rooms",
      field_rooms: "Rooms on top of the living area",
      field_unlimited: "Unlimited time per visit",
      field_visit_minutes: "Time per visit",
      field_residents: "Residents",
      field_area: "Area",
      field_door: "Door contact",
      field_weekdays: "Weekdays",
      field_start: "From",
      field_end: "To",
      field_note: "Note",
      field_log_visits: "Keep a visit log",
      field_resume_minutes: "Time to be seen again after a restart",
      field_log_grid_minutes: "Grid of the visit log",
      field_log_keep_days: "Keep single visits",
      field_log_keep_months: "Keep monthly totals",
      help_name: "Shown on this page, in events and as the name of the guest's device. Up to 100 characters.",
      help_trackers: "The guest is home when one of them is home.",
      help_kind: "Locked: never counts. Once: until the end or until the guest leaves for longer than the grace time. Permanent until: until the end. Permanent: always.",
      help_until: "When the approval ends.",
      help_grace: "A return within this time continues the visit; afterwards a once approval ends. 1 to 240 minutes.",
      help_all_rooms: "The guest may enter every lockable room.",
      help_rooms: "The living area is always free; these lockable rooms on top.",
      help_unlimited: "A visit counts as long as the guest is home.",
      help_visit_minutes: "After this time the guest no longer counts and the status reads Time up. 1 to 1440 minutes.",
      help_residents: "The room lock applies only while none of them is home.",
      help_note: "Only administrators see it, here on this page.",
      help_log_visits: "Date, start and length of each visit on a {grid}-minute grid; single visits for {days} days, monthly totals for {months} months. Switched off, the log so far is deleted.",
      help_resume_minutes: "A guest who counted before a restart continues the visit when a tracker reports home within this time. 1 to 60 minutes.",
      help_log_grid_minutes: "Start and length of a logged visit are rounded to it. 1 to 60 minutes.",
      help_log_keep_days: "Then a visit is deleted; its monthly total stays. 1 to 3650 days.",
      help_log_keep_months: "Then the monthly total is deleted. 1 to 120 months.",
      kind_off: "Locked",
      kind_once: "Once until",
      kind_until: "Permanent until",
      kind_permanent: "Permanent",
      expired: "expired",
      outsideWindows: "outside the time windows",
      approvalSection: "Approval",
      roomsSection: "Rooms and time",
      windows: "Time windows",
      windowsHelp: "Without a time window the approval applies at any time.",
      addWindow: "Add time window",
      removeWindow: "Remove time window",
      addRoom: "Add room",
      removeRoom: "Remove room",
      lockableRooms: "Lockable rooms",
      roomsHelp: "A lockable room is an area with exactly one door contact.",
      noRooms: "No lockable rooms set yet.",
      setUpRooms: "Set up rooms",
      allRooms: "all rooms",
      unlimited: "unlimited",
      minutes: "{n} min",
      unitMin: "min",
      unitDays: "days",
      unitMonths: "months",
      status_counting: "Counts as home",
      status_time_up: "Time up",
      status_approval_expired: "Approval expired",
      status_not_approved: "Home without approval",
      status_resuming: "Waiting after restart",
      status_away: "Away",
      status_inactive: "No approval",
      visitEnds: "until {time}",
      lockActive: "Room lock on: {locked} locked.",
      lockActiveHelp: "Only guests are home. Free: {free}. The lock ends when a resident comes home or no guest counts.",
      lockOff: "Room lock off.",
      lockOffHelp: "A resident is home or no guest counts.",
      none: "none",
      timingsSection: "Timings",
      logSection: "Visit log",
      mediaSection: "Photo and note",
      photoHelp: "Shown on dashboards, as a person's picture is.",
      choosePhoto: "Choose photo",
      removePhoto: "Remove photo",
      logOffNote: "Saving deletes the visit log kept so far.",
      logRunning: "Visit running since {time}",
      logMonth: "This month: {visits}, {hours} h",
      logLastMonth: "Last month: {visits}, {hours} h",
      visitOne: "1 visit",
      visitMany: "{count} visits",
      logNone: "No finished visits yet.",
      logExport: "Export as CSV",
      logDelete: "Delete log",
      logDeleteConfirm: "Delete the visit log of {name}?",
      csvHeader: "Date;Start;End;Hours",
      setupTitle: "Setup",
      setupHelp: "Guest Access needs the residents and the lockable rooms for the room lock, and guests to approve. Each step leads to its page.",
      stepResidents: "Residents",
      stepRooms: "Lockable rooms",
      stepGuests: "Guests",
      stepDone: "done",
      stepOpen: "open",
      noneYet: "None yet",
      guestCount: "{n} guests",
      next: "Continue",
      about: "Guest Access {version}",
      aboutCommit: "Guest Access {version} · commit {commit}",
      asOf: "As of {time}",
      refresh: "Refresh",
      integration: "Integration in Home Assistant",
      info: "Explanation",
      errDetail: "Message",
      e_not_loaded: "Guest Access is not set up.",
      e_not_found: "This is gone meanwhile. Refresh and try again.",
      e_invalid_format: "The input does not fit.",
      e_unauthorized: "This needs an administrator.",
      e_other: "That did not work. Please try again.",
      weekdays: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
      weekdaysShort: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
    },
    de: {
      title: "Guest Access",
      tabGuests: "Gäste",
      tabSetup: "Einrichtung",
      pageList: "Gäste",
      pageOverview: "Übersicht",
      pageResidents: "Bewohner",
      pageRooms: "Räume",
      pageTimings: "Zeiten",
      viewDetails: "Gast",
      viewApproval: "Freigabe",
      viewRooms: "Räume und Zeit",
      viewLog: "Besuchsprotokoll",
      guests: "Gäste",
      addGuest: "Gast hinzufügen",
      newGuest: "Neuer Gast",
      noGuests: "Noch keine Gäste.",
      noGuestsHelp: "Ein Gast zählt nur mit Freigabe als daheim.",
      lock: "Sperren",
      lockConfirm: "{name} sperren? Der Gast zählt dann nicht mehr als zuhause, bis er wieder freigegeben wird.",
      delete: "Löschen",
      deleteGuest: "Gast löschen",
      deleteConfirm: "{name} mit Gerät und Entitäten löschen?",
      cancel: "Abbrechen",
      save: "Speichern",
      field_name: "Name",
      field_trackers: "Tracker",
      field_kind: "Freigabe",
      field_until: "Bis",
      field_grace: "Kulanzzeit",
      field_all_rooms: "Alle Räume",
      field_rooms: "Räume zusätzlich zum Wohnbereich",
      field_unlimited: "Unbegrenzte Dauer je Besuch",
      field_visit_minutes: "Dauer je Besuch",
      field_residents: "Bewohner",
      field_area: "Bereich",
      field_door: "Türkontakt",
      field_weekdays: "Wochentage",
      field_start: "Von",
      field_end: "Bis",
      field_note: "Notiz",
      field_log_visits: "Besuchsprotokoll führen",
      field_resume_minutes: "Wiedererkennung nach Neustart",
      field_log_grid_minutes: "Raster des Besuchsprotokolls",
      field_log_keep_days: "Einzelne Besuche aufbewahren",
      field_log_keep_months: "Monatssummen aufbewahren",
      help_name: "Erscheint auf dieser Seite, in Ereignissen und als Name des Geräts des Gasts. Bis zu 100 Zeichen.",
      help_trackers: "Der Gast ist daheim, sobald einer davon daheim ist.",
      help_kind: "Gesperrt: zählt nie. Einmalig: bis zum Ende oder bis der Gast länger als die Kulanzzeit weg ist. Dauerhaft bis: bis zum Ende. Dauerhaft: immer.",
      help_until: "Wann die Freigabe endet.",
      help_grace: "Wer in dieser Zeit zurückkommt, setzt den Besuch fort; danach endet eine einmalige Freigabe. 1 bis 240 Minuten.",
      help_all_rooms: "Der Gast darf jeden sperrbaren Raum betreten.",
      help_rooms: "Der Wohnbereich ist immer frei; diese sperrbaren Räume zusätzlich.",
      help_unlimited: "Ein Besuch zählt, solange der Gast daheim ist.",
      help_visit_minutes: "Nach dieser Zeit zählt der Gast nicht mehr, der Status lautet Zeit um. 1 bis 1440 Minuten.",
      help_residents: "Die Raumsperre gilt nur, solange keiner von ihnen daheim ist.",
      help_note: "Sehen nur Administratoren, hier auf dieser Seite.",
      help_log_visits: "Datum, Beginn und Dauer je Besuch, auf {grid} Minuten gerundet; einzelne Besuche {days} Tage, Monatssummen {months} Monate. Ausgeschaltet wird das bisherige Protokoll gelöscht.",
      help_resume_minutes: "Ein Gast, der vor einem Neustart zählte, setzt den Besuch fort, wenn ein Tracker in dieser Zeit daheim meldet. 1 bis 60 Minuten.",
      help_log_grid_minutes: "Beginn und Dauer eines protokollierten Besuchs werden darauf gerundet. 1 bis 60 Minuten.",
      help_log_keep_days: "Danach wird ein Besuch gelöscht; seine Monatssumme bleibt. 1 bis 3650 Tage.",
      help_log_keep_months: "Danach wird die Monatssumme gelöscht. 1 bis 120 Monate.",
      kind_off: "Gesperrt",
      kind_once: "Einmalig bis",
      kind_until: "Dauerhaft bis",
      kind_permanent: "Dauerhaft",
      expired: "abgelaufen",
      outsideWindows: "außerhalb der Zeitfenster",
      approvalSection: "Freigabe",
      roomsSection: "Räume und Zeit",
      windows: "Zeitfenster",
      windowsHelp: "Ohne Zeitfenster gilt die Freigabe jederzeit.",
      addWindow: "Zeitfenster hinzufügen",
      removeWindow: "Zeitfenster entfernen",
      addRoom: "Raum hinzufügen",
      removeRoom: "Raum entfernen",
      lockableRooms: "Sperrbare Räume",
      roomsHelp: "Sperrbar ist ein Bereich mit genau einem Türkontakt.",
      noRooms: "Noch keine sperrbaren Räume festgelegt.",
      setUpRooms: "Räume einrichten",
      allRooms: "alle Räume",
      unlimited: "unbegrenzt",
      minutes: "{n} min",
      unitMin: "min",
      unitDays: "Tage",
      unitMonths: "Monate",
      status_counting: "Zählt als daheim",
      status_time_up: "Zeit um",
      status_approval_expired: "Freigabe abgelaufen",
      status_not_approved: "Daheim ohne Freigabe",
      status_resuming: "Wartet nach Neustart",
      status_away: "Weg",
      status_inactive: "Ohne Freigabe",
      visitEnds: "bis {time}",
      lockActive: "Raumsperre an: {locked} gesperrt.",
      lockActiveHelp: "Nur Gäste sind daheim. Frei: {free}. Die Sperre endet, wenn ein Bewohner heimkommt oder kein Gast mehr zählt.",
      lockOff: "Raumsperre aus.",
      lockOffHelp: "Ein Bewohner ist daheim oder kein Gast zählt.",
      none: "keine",
      timingsSection: "Zeiten",
      logSection: "Besuchsprotokoll",
      mediaSection: "Foto und Notiz",
      photoHelp: "Erscheint auf Dashboards, wie das Bild einer Person.",
      choosePhoto: "Foto wählen",
      removePhoto: "Foto entfernen",
      logOffNote: "Beim Speichern wird das bisherige Besuchsprotokoll gelöscht.",
      logRunning: "Besuch läuft seit {time}",
      logMonth: "Dieser Monat: {visits}, {hours} h",
      logLastMonth: "Letzter Monat: {visits}, {hours} h",
      visitOne: "1 Besuch",
      visitMany: "{count} Besuche",
      logNone: "Noch keine abgeschlossenen Besuche.",
      logExport: "Als CSV exportieren",
      logDelete: "Protokoll löschen",
      logDeleteConfirm: "Besuchsprotokoll von {name} löschen?",
      csvHeader: "Datum;Beginn;Ende;Stunden",
      setupTitle: "Einrichtung",
      setupHelp: "Guest Access braucht für die Raumsperre die Bewohner und die sperrbaren Räume, und Gäste zum Freigeben. Jeder Schritt führt zu seiner Seite.",
      stepResidents: "Bewohner",
      stepRooms: "Sperrbare Räume",
      stepGuests: "Gäste",
      stepDone: "erledigt",
      stepOpen: "offen",
      noneYet: "Noch keine",
      guestCount: "{n} Gäste",
      next: "Weiter",
      about: "Guest Access {version}",
      aboutCommit: "Guest Access {version} · Commit {commit}",
      asOf: "Stand {time}",
      refresh: "Aktualisieren",
      integration: "Integration in Home Assistant",
      info: "Erklärung",
      errDetail: "Meldung",
      e_not_loaded: "Guest Access ist nicht eingerichtet.",
      e_not_found: "Das gibt es inzwischen nicht mehr. Aktualisieren und erneut versuchen.",
      e_invalid_format: "Die Eingabe passt nicht.",
      e_unauthorized: "Dafür braucht es einen Administrator.",
      e_other: "Das hat nicht geklappt. Bitte erneut versuchen.",
      weekdays: ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
      weekdaysShort: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
    },
  };

  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const pad = (n) => String(n).padStart(2, "0");
  const icon = (name, attrs = "") => `<ha-svg-icon path="${MDI[name]}"${attrs ? ` ${attrs}` : ""}></ha-svg-icon>`;
  // An ISO time as the value of a datetime selector, in local time
  const localValue = (iso) => {
    if (!iso) return undefined;
    const d = new Date(iso);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:00`;
  };
  const withSeconds = (time) => (time && time.length === 5 ? `${time}:00` : time);
  const withoutSeconds = (time) => (time || "").slice(0, 5);
  // A photo is an image uploaded to Home Assistant, served by its ID
  const pictureUrl = (id) => `/api/image/serve/${id}/512x512`;

  // In-app navigation like Home Assistant's own links, no page reload
  const navigate = (path, replace = false) => {
    if (replace) window.history.replaceState(null, "", path);
    else window.history.pushState(null, "", path);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace } }));
  };

  // Numbers as Home Assistant writes them: the number format of the user's profile
  const numberLocale = (hass) => {
    const format = hass?.locale?.number_format;
    if (format === "system") return undefined;
    return { comma_decimal: "en-US", decimal_comma: "de", space_comma: "fr", none: "en-US" }[format] ||
      hass?.locale?.language || hass?.language || "en";
  };
  // A number for reading, with up to d decimals
  const formatNumber = (hass, v, d = 0) => (Number.isFinite(v)
    ? v.toLocaleString(numberLocale(hass), { maximumFractionDigits: d, useGrouping: hass?.locale?.number_format !== "none" })
    : "–");
  // A number in a text field, and back: typing takes a point or a comma
  const fieldNumber = (hass, v) => (Number.isFinite(v) ? v.toLocaleString(numberLocale(hass), { useGrouping: false, maximumFractionDigits: 3 }) : "");
  const numOrNull = (v) => {
    const n = parseFloat(String(v).replace(",", "."));
    return Number.isFinite(n) ? n : null;
  };

  // An error of a call: one line by its kind, what Home Assistant said for the (i)
  const errorText = (t, err) => {
    const text = (err?.code && t[`e_${err.code}`]) || t.e_other;
    const said = err?.message || (typeof err === "string" ? err : "");
    return { text, detail: said && said !== text ? said : "" };
  };

  const STYLE = `
    /* The panel's own container has no height of its own: the page takes the window */
    :host { display: block; height: 100vh; height: 100dvh; background: var(--primary-background-color);
      color: var(--primary-text-color); font-family: var(--ha-font-family-body, Roboto, Noto, sans-serif);
      font-size: var(--ha-font-size-m, 14px); line-height: 1.5; -webkit-font-smoothing: antialiased; }
    * { box-sizing: border-box; }
    hass-tabs-subpage { height: 100%; }
    .subname { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .actions { display: flex; align-items: center; }
    .stamp { color: var(--secondary-text-color); font-size: var(--ha-font-size-m, 14px); white-space: nowrap;
      margin-inline-end: 4px; font-variant-numeric: tabular-nums; }
    @media (max-width: 600px) { .stamp { display: none; } }
    #refresh.loading { animation: spin 1s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .page { display: flex; flex-direction: column; min-height: 100%; }
    .subtabs { flex: none; padding: 0 16px; }
    .narrow .subtabs { padding: 0 4px; }
    .sheet { width: 100%; max-width: 860px; margin: 0 auto; padding: 16px 16px 88px; display: flex; flex-direction: column; gap: 16px; }
    .narrow .sheet { padding: 8px 8px 88px; gap: 8px; }
    ha-card { display: block; overflow: hidden; }
    /* The title of a card as Home Assistant draws it, with room for the (i) at its end */
    .card-header { display: flex; align-items: center; gap: 4px; margin: 0; padding: 12px 8px 12px 16px; min-height: 48px;
      color: var(--ha-card-header-color, var(--primary-text-color)); font-size: var(--ha-card-header-font-size, var(--ha-font-size-2xl, 24px));
      font-weight: var(--ha-font-weight-normal, 400); line-height: var(--ha-line-height-condensed, 1.2); }
    .card-header ha-icon-button.help { margin-inline-start: auto; }
    .card-content { padding: 0 16px 16px; }
    .card-content.top { padding-top: 16px; }
    ha-card.list .card-content, ha-card.settings .card-content { padding: 0 0 8px; }
    .card-actions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; align-items: center;
      padding: 8px 16px; border-top: 1px solid var(--divider-color); }
    .card-actions.solo { border-top: none; }
    ha-icon-button.help { --mdc-icon-button-size: 32px; --mdc-icon-size: 18px; --ha-icon-button-size: 32px; color: var(--secondary-text-color); flex: none; }
    ha-tooltip { --max-width: min(360px, 90vw); }
    .alertact { display: flex; align-items: center; gap: 4px; }
    ha-alert { display: block; }
    /* Settings: Home Assistant's rows, the field at the end, below the name on a phone */
    ha-settings-row { --settings-row-content-width: 100%; padding: 0 16px; }
    ha-settings-row + ha-settings-row:not([narrow]) { border-top: 1px solid var(--divider-color); }
    ha-settings-row .heading { display: inline-flex; align-items: center; gap: 2px; }
    ha-settings-row .haform { width: 320px; max-width: 100%; }
    ha-settings-row.num .haform { width: 180px; }
    ha-settings-row.bool .haform { width: auto; }
    ha-settings-row[narrow] .haform { width: 100%; }
    /* A list row that opens a guest or a step of the setup */
    .item { display: flex; align-items: center; gap: 16px; padding: 8px 8px 8px 16px; min-height: 72px; cursor: pointer; }
    .item:hover, .item:focus-visible { background: var(--secondary-background-color); outline: none; }
    .item .lead { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex: none; }
    .item img.lead { object-fit: cover; }
    .item .text { flex: 1; min-width: 0; }
    .item .headline { display: block; font-size: var(--ha-font-size-l, 16px); font-weight: var(--ha-font-weight-medium, 500); line-height: 24px; }
    .item .supporting { display: block; font-size: var(--ha-font-size-m, 14px); color: var(--secondary-text-color); line-height: 20px; }
    .item .next { color: var(--secondary-text-color); display: flex; }
    .lead.step { background: var(--secondary-background-color); color: var(--primary-text-color); }
    .lead.step.done { background: var(--success-color, #43a047); color: var(--text-primary-color, #fff); }
    .empty { display: flex; align-items: center; gap: 4px; padding: 0 16px 8px; color: var(--secondary-text-color); }
    .line { margin: 4px 0; color: var(--secondary-text-color); }
    .entry { display: flex; align-items: flex-start; gap: 8px; padding: 8px 0; border-top: 1px solid var(--divider-color); }
    .entry:first-child { border-top: none; }
    .entry .haform { flex: 1; min-width: 0; }
    .entry ha-icon-button { margin-top: 4px; color: var(--secondary-text-color); }
    .media { display: flex; align-items: center; gap: 16px; padding: 0 16px 8px; flex-wrap: wrap; }
    .media .avatar { width: 96px; height: 96px; border-radius: 50%; flex: none; object-fit: cover; display: flex;
      align-items: center; justify-content: center; background: var(--secondary-background-color); color: var(--secondary-text-color);
      --mdc-icon-size: 48px; }
    .media .media-actions { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; }
    .visits { margin: 8px 0; }
    .visit { display: flex; justify-content: space-between; gap: 8px; padding: 6px 0; border-top: 1px solid var(--divider-color); font-variant-numeric: tabular-nums; }
    .visit:first-child { border-top: none; }
    .log-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    .loading-sheet { display: flex; justify-content: center; padding: 32px; }
    /* Name and version at the bottom of the setup overview, centred */
    .about { text-align: center; color: var(--secondary-text-color); font-size: var(--ha-font-size-s, 12px); padding: 8px 0 24px; }
  `;

  class GuestAccessPanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._data = null;
      // The visit logs loaded so far, by guest
      this._logs = {};
      this._page = "list";
      this._key = null;
      this._view = "details";
      // The guest being edited (a draft of the open subpage), the settings typed but not saved
      this._form = null;
      this._settings = null;
      // A pending confirmation: {action: "lock" | "delete" | "logDelete", id, name}
      this._confirm = null;
      // The error of the last call, and of the subscription
      this._note = null;
      this._loadError = null;
      this._forms = {};
      this._hid = 0;
      this._bindOnce();
    }

    set hass(hass) {
      const first = !this._hass;
      this._hass = hass;
      for (const el of this.shadowRoot.querySelectorAll("hass-tabs-subpage, ha-form")) el.hass = hass;
      if (first) {
        this._subscribe();
        this._render();
      }
    }

    set narrow(narrow) {
      this._narrow = narrow;
      this._render();
    }

    // The address: /<area>/<page>, a guest ?key=…&view=…; an old address goes to
    // its new place, an area alone to its first page, nothing to the guests (to the
    // setup overview while nothing is set up)
    set route(route) {
      const parts = (route?.path || "").split("/").filter(Boolean);
      const search = window.location.search;
      if (OLD_PAGES[parts[0]]) {
        navigate(`${PANEL_PATH}/${OLD_PAGES[parts[0]]}${search}`, true);
        return;
      }
      const area = AREAS.find((a) => a[0] === parts[0]);
      if (!area) {
        navigate(this._data && this._nothingSetUp() ? `${PANEL_PATH}/setup/overview` : `${PANEL_PATH}/guests/list`, true);
        this._defaulted = !this._data;
        return;
      }
      if (!area[3].some(([p]) => p === parts[1])) {
        navigate(`${PANEL_PATH}/${area[0]}/${area[3][0][0]}${search}`, true);
        return;
      }
      // The same address again (Home Assistant after the query was read): nothing to do
      if (window.location.pathname + search === this._href && this._page === parts[1]) return;
      this._href = window.location.pathname + search;
      this._route = { prefix: PANEL_PATH, path: `/${area[0]}/${parts[1]}` };
      const query = new URLSearchParams(search);
      this._setPage(parts[1], parts[1] === "list" ? query.get("key") : null, query.get("view"));
    }

    connectedCallback() {
      if (this._hass && !this._unsub) this._subscribe();
      // Home Assistant passes a new route only when the path changes: an address
      // that changes only its query (another guest, &view=log) is read here
      this._onLocation = () => {
        const { pathname, search } = window.location;
        if (!pathname.startsWith(`${PANEL_PATH}/`) || pathname + search === this._href) return;
        this.route = { prefix: PANEL_PATH, path: pathname.slice(PANEL_PATH.length) };
      };
      window.addEventListener("location-changed", this._onLocation);
      window.addEventListener("popstate", this._onLocation);
    }

    disconnectedCallback() {
      window.removeEventListener("location-changed", this._onLocation);
      window.removeEventListener("popstate", this._onLocation);
      clearTimeout(this._retry);
      // Leaving the page drops photos uploaded in an open guest but not saved
      this._dropUploads(this._form);
      this._form = null;
      this._confirm = null;
      if (this._unsub) {
        this._unsub.then((unsub) => unsub()).catch(() => {});
        this._unsub = null;
      }
    }

    get _lang() {
      return this._hass?.language || "en";
    }

    get _texts() {
      return TEXTS[this._lang.split("-")[0]] || TEXTS.en;
    }

    _t(key, values = {}) {
      const text = this._texts[key] ?? TEXTS.en[key] ?? key;
      if (typeof text !== "string") return text;
      // A function as replacement keeps "$" in names as they are
      return text.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
    }

    _num(v, d = 0) {
      return formatNumber(this._hass, v, d);
    }

    // ---- Data ----

    _subscribe() {
      this._unsub = this._hass.connection.subscribeMessage(
        (data) => {
          this._data = data;
          this._stamp = new Date();
          this._loading = false;
          this._loadError = null;
          // Opened without an address while nothing is set up: start at the setup
          if (this._defaulted) {
            this._defaulted = false;
            if (this._nothingSetUp() && this._page === "list" && !this._key) {
              navigate(`${PANEL_PATH}/setup/overview`, true);
              return;
            }
          }
          this._render();
        },
        { type: `${DOMAIN}/subscribe` },
      );
      const attempt = this._unsub;
      attempt.catch((err) => {
        this._loading = false;
        this._loadError = errorText(this._texts, err);
        this._render();
        // The entry may still be loading, after an update say: try again shortly,
        // as long as the page is open and nothing else subscribed meanwhile
        if (this._unsub !== attempt) return;
        this._unsub = null;
        clearTimeout(this._retry);
        this._retry = setTimeout(() => {
          if (this.isConnected && this._hass && !this._unsub) this._subscribe();
        }, RETRY_MS);
      });
    }

    // A guest's visit log, or null until it is there. It is not part of the data
    // pushed after every change: the page loads it for the guest whose log it
    // shows, and again once a push says something changed
    _log(id) {
      const entry = (this._logs[id] ??= { log: null, stamp: null, loading: false });
      if (!entry.loading && entry.stamp !== this._stamp) this._loadLog(id, entry);
      return entry.log;
    }

    async _loadLog(id, entry) {
      entry.loading = true;
      entry.stamp = this._stamp;
      try {
        entry.log = await this._hass.callWS({ type: `${DOMAIN}/visit_log`, guest_id: id });
      } catch {
        // A guest deleted meanwhile: the next push takes the view away
        entry.log = null;
      }
      entry.loading = false;
      // Only the log view shows it; elsewhere a redraw could take a typed input
      if (this._view === "log") this._redraw = true;
      this._render();
    }

    // The refresh button: subscribe again, the data come anew over the WebSocket, no reload
    async _refresh() {
      if (this._loading || !this._hass) return;
      this._loading = true;
      this._render();
      clearTimeout(this._retry);
      const old = this._unsub;
      this._unsub = null;
      if (old) await old.then((unsub) => unsub()).catch(() => {});
      if (this.isConnected && !this._unsub) this._subscribe();
      else this._loading = false;
      this._render();
    }

    // One call of the API; an error goes to the page as one line
    async _call(message) {
      this._busy = true;
      this._note = null;
      this._render();
      try {
        return await this._hass.callWS(message);
      } catch (err) {
        this._note = errorText(this._texts, err);
        throw err;
      } finally {
        this._busy = false;
        this._render();
      }
    }

    _nothingSetUp() {
      const d = this._data;
      return !!d && !d.settings.residents.length && !d.settings.rooms.length && !d.guests.length;
    }

    // ---- Pages ----

    _setPage(page, key, view) {
      const keyChanged = key !== this._key;
      if (page !== this._page || keyChanged) {
        this._note = null;
        this._confirm = null;
      }
      // Another guest: the draft of the one before goes, with its photos not saved
      if (keyChanged && this._form?.key !== key) {
        this._dropUploads(this._form);
        this._form = null;
      }
      this._page = page;
      this._key = key;
      this._view = GUEST_VIEWS.some(([v]) => v === view) ? view : "details";
      this._render();
    }

    // The draft of the open guest, made from the guest when it opens
    _guestForm() {
      if (this._page !== "list" || !this._key) return null;
      if (this._form?.key === this._key) return this._form;
      let guest = null;
      if (this._key !== "new") {
        guest = this._data?.guests.find((g) => g.id === this._key);
        if (!guest) return null;
      } else if (!this._data) return null;
      const a = guest?.approval;
      const f = {
        key: this._key,
        id: guest?.id ?? null,
        originalName: guest?.name ?? "",
        main: { name: guest?.name ?? "", trackers: guest ? [...guest.trackers] : [] },
        approval: { kind: a?.kind ?? "once", until: localValue(a?.until), grace: guest?.grace_minutes ?? 15 },
        windows: (a?.windows ?? []).map((w) => ({ weekdays: w.weekdays.map(String), start: withSeconds(w.start), end: withSeconds(w.end) })),
        rooms: {
          all_rooms: guest?.all_rooms ?? false,
          rooms: guest ? [...guest.rooms] : [],
          unlimited: guest ? guest.visit_minutes === null : false,
          visit_minutes: guest?.visit_minutes ?? 60,
        },
        log: { log_visits: guest?.log_visits ?? false },
        wasLogging: guest?.log_visits ?? false,
        media: { picture: guest?.picture ?? null, note: guest?.note ?? "" },
        // The photo is sent only when it changed here, so a draft made before
        // another change neither undoes that change nor sends a photo long gone
        originalPicture: guest?.picture ?? null,
        // Images uploaded while the guest is open; the ones not saved are deleted
        uploaded: [],
      };
      f.base = JSON.stringify(this._guestMessage(f));
      this._form = f;
      return f;
    }

    // What saving the guest sends; the photo always, for comparing
    _guestMessage(f) {
      const kind = f.approval.kind;
      const withEnd = kind === "once" || kind === "until";
      const withWindow = kind === "until" || kind === "permanent";
      const until = withEnd && f.approval.until ? new Date(f.approval.until.replace(" ", "T")) : null;
      return {
        type: `${DOMAIN}/save_guest`,
        name: (f.main.name || "").trim(),
        trackers: f.main.trackers || [],
        approval: {
          kind,
          until: until && !isNaN(until) ? until.toISOString() : null,
          windows: withWindow
            ? f.windows.map((w) => ({ weekdays: (w.weekdays || []).map(Number).sort(), start: withoutSeconds(w.start), end: withoutSeconds(w.end) }))
            : [],
        },
        rooms: f.rooms.all_rooms ? [] : f.rooms.rooms || [],
        all_rooms: !!f.rooms.all_rooms,
        visit_minutes: f.rooms.unlimited ? null : f.rooms.visit_minutes,
        grace_minutes: f.approval.grace,
        log_visits: !!f.log.log_visits,
        note: (f.media.note || "").trim(),
        picture: f.media.picture,
      };
    }

    get _guestDirty() {
      const f = this._form;
      return !!f && f.key === this._key && JSON.stringify(this._guestMessage(f)) !== f.base;
    }

    // The settings as typed, or as saved
    _settingsNow() {
      if (this._settings) return this._settings;
      const s = this._data.settings;
      return {
        residents: [...s.residents],
        rooms: s.rooms.map((room) => ({ ...room })),
        resume_minutes: s.resume_minutes,
        log_grid_minutes: s.log_grid_minutes,
        log_keep_days: s.log_keep_days,
        log_keep_months: s.log_keep_months,
      };
    }

    _settingsMessage(s) {
      return {
        type: `${DOMAIN}/save_settings`,
        residents: s.residents || [],
        rooms: s.rooms.filter((r) => r.area_id || r.door),
        resume_minutes: s.resume_minutes,
        log_grid_minutes: s.log_grid_minutes,
        log_keep_days: s.log_keep_days,
        log_keep_months: s.log_keep_months,
      };
    }

    get _settingsDirty() {
      if (!this._settings || !this._data) return false;
      const saved = { ...this._settings, ...this._data.settings, rooms: this._data.settings.rooms };
      return JSON.stringify(this._settingsMessage(this._settings)) !== JSON.stringify(this._settingsMessage(saved));
    }

    _setSetting(values) {
      this._settings = { ...this._settingsNow(), ...values };
    }

    // ---- Names and texts ----

    _areaName(areaId) {
      return this._hass.areas?.[areaId]?.name || areaId;
    }

    _entityName(entityId) {
      return this._hass.states[entityId]?.attributes?.friendly_name || entityId;
    }

    _time(iso) {
      return new Date(iso).toLocaleString(this._lang, { dateStyle: "short", timeStyle: "short" });
    }

    _rooms(ids) {
      return ids.map((id) => this._areaName(id)).join(", ") || this._t("none");
    }

    _approvalText(guest) {
      const a = guest.approval;
      let text = this._t(`kind_${a.kind}`);
      if (a.until) text += ` ${this._time(a.until)}`;
      const windows = a.windows.map(
        (w) => `${w.weekdays.map((d) => this._t("weekdaysShort")[d]).join(", ")} ${withoutSeconds(w.start)}–${withoutSeconds(w.end)}`,
      );
      if (windows.length) text += ` · ${windows.join("; ")}`;
      if (a.kind !== "off" && !guest.state.approval_valid) {
        // Not valid now: either past its end or, before that, outside every window
        const over = a.until && new Date(a.until) <= new Date();
        text += ` (${this._t(over || !windows.length ? "expired" : "outsideWindows")})`;
      }
      return text;
    }

    // The status comes from the integration, as on the guest's status sensor
    _statusText(guest) {
      const s = guest.state;
      let text = this._t(`status_${s.status}`);
      if (s.counting && s.visit_ends) text += ` ${this._t("visitEnds", { time: this._time(s.visit_ends) })}`;
      return text;
    }

    _minutesText(n) {
      return this._t("minutes", { n: this._num(n) });
    }

    // Hours of the visit log, up to two decimals in the number format
    _hours(minutes) {
      return this._num(minutes / 60, 2);
    }

    // ---- Building blocks ----

    // The (i): Home Assistant's icon button with its tooltip; a tap or Enter shows it, as hovering does
    _help(text) {
      if (!text) return "";
      const id = `help${++this._hid}`;
      return `<ha-icon-button class="help" id="${id}" path="${MDI.info}" label="${esc(this._t("info"))}"></ha-icon-button>` +
        `<ha-tooltip for="${id}" placement="top" trigger="hover click">${esc(text)}</ha-tooltip>`;
    }

    // A card, its title with an (i) when it has something to explain
    _card(title, body, { help = "", cls = "", actions = "" } = {}) {
      const head = title ? `<h1 class="card-header">${esc(title)}${this._help(help)}</h1>` : "";
      return `<ha-card class="${cls}">${head}<div class="card-content${title ? "" : " top"}">${body}</div>` +
        `${actions ? `<div class="card-actions">${actions}</div>` : ""}</ha-card>`;
    }

    // One line of state, the why behind its (i), maybe an action
    _alert(kind, text, help = "", action = "") {
      const end = action || help ? `<span slot="action" class="alertact">${action}${this._help(help)}</span>` : "";
      return `<ha-alert alert-type="${kind}">${esc(text)}${end}</ha-alert>`;
    }

    _errHtml(e) {
      return this._alert("error", e.text, e.detail ? `${this._t("errDetail")}: ${e.detail}` : "");
    }

    _btn(act, label, { kind = "", data = "", disabled = false } = {}) {
      const look = kind === "filled" ? "" : kind === "danger" ? ' appearance="plain" variant="danger"' : ' appearance="plain"';
      return `<ha-button${look} data-act="${act}"${data}${disabled || this._busy ? " disabled" : ""}>${esc(label)}</ha-button>`;
    }

    // Removing and locking ask first, in the page, as Home Assistant's own pages do
    _confirmHtml(action) {
      const c = this._confirm;
      if (!c || c.action !== action) return "";
      const label = action === "lock" ? "lock" : action === "logDelete" ? "logDelete" : "delete";
      return `<ha-alert alert-type="warning">${esc(this._t(`${action}Confirm`, { name: c.name }))}` +
        `<ha-button slot="action" appearance="plain" id="confirm-cancel" data-act="confirm-cancel">${esc(this._t("cancel"))}</ha-button>` +
        `<ha-button slot="action" variant="danger" id="confirm-ok" data-act="confirm-ok">${esc(this._t(label))}</ha-button></ha-alert>`;
    }

    // A place for an ha-form, made once the HTML is in the page (_hydrate)
    _formSlot(id, schema, data, onChange, aria = "") {
      const clean = Object.fromEntries(Object.entries(data).filter(([, v]) => v !== null && v !== undefined));
      this._forms[id] = { schema, data: clean, onChange, aria };
      return `<div class="haform" data-form="${esc(id)}" data-v="${esc(JSON.stringify(clean))}"></div>`;
    }

    // A setting: Home Assistant's row with its name and (i), the field at the end.
    // kind: "num" (a number as text in the number format, with its unit), "bool",
    // "required" (a field that cannot be emptied), "" (any other)
    _row(id, name, selector, value, onChange, { kind = "", unit = "", help = null, values = {} } = {}) {
      const label = this._t(`field_${name}`);
      const field = kind === "num"
        ? { name, label: "", num: true, selector: { text: unit ? { suffix: unit } : {} } }
        : { name, label: "", required: kind === "required", selector };
      const slot = this._formSlot(id, [field], { [name]: value }, (v) => onChange(v[name]), label);
      return `<ha-settings-row class="${kind}"${this._narrow ? " narrow" : ""} wrap-heading>` +
        `<span slot="heading" class="heading">${esc(label)}${this._help(help ?? this._t(`help_${name}`, values))}</span>${slot}</ha-settings-row>`;
    }

    // The input deep in Home Assistant's field gets the name the row shows beside it
    async _ariaName(form, name, tries = 10) {
      await form.updateComplete;
      const find = (root) => {
        for (const el of root.querySelectorAll("*")) {
          if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.getAttribute("role") === "switch") return el;
          const deep = el.shadowRoot && find(el.shadowRoot);
          if (deep) return deep;
        }
        return null;
      };
      const input = form.shadowRoot && find(form.shadowRoot);
      if (input) input.setAttribute("aria-label", name);
      else if (tries > 0) setTimeout(() => this._ariaName(form, name, tries - 1), 100);
    }

    _hydrate(root) {
      for (const slot of root.querySelectorAll("[data-form]")) {
        const spec = this._forms[slot.dataset.form];
        if (!spec) continue;
        const form = document.createElement("ha-form");
        form.hass = this._hass;
        form.schema = spec.schema;
        // Numbers go into the fields as text in the number format, and come back as numbers
        const nums = new Set(spec.schema.filter((f) => f.num).map((f) => f.name));
        const shown = (d) => Object.fromEntries(Object.entries(d).map(([k, v]) => [k, nums.has(k) && typeof v === "number" ? fieldNumber(this._hass, v) : v]));
        const read = (d) => Object.fromEntries(Object.entries(d).map(([k, v]) => [k, nums.has(k) ? (v === "" || v == null ? null : numOrNull(v)) : v]));
        form.data = shown(spec.data);
        form.computeLabel = (s) => s.label ?? this._t(`field_${s.name}`);
        if (spec.aria) this._ariaName(form, spec.aria);
        form.addEventListener("value-changed", (e) => {
          form.data = e.detail.value;
          spec.onChange(read(e.detail.value));
        });
        slot.append(form);
      }
    }

    // A redraw while a field has the focus would lose the input; a change that
    // changes other fields asks for the redraw itself
    _typing() {
      if (this._redraw) return false;
      const el = this.shadowRoot.activeElement;
      return !!el && (el.tagName === "HA-FORM" || el.tagName === "TEXTAREA");
    }

    _tabGroup(id, items, active) {
      return `<ha-tab-group id="${id}" class="subtabs">${items
        .map(([key, label]) => `<ha-tab-group-tab slot="nav" panel="${key}"${key === active ? " active" : ""}>${esc(this._t(label))}</ha-tab-group-tab>`)
        .join("")}</ha-tab-group>`;
    }

    // ---- Drawing ----

    get _subName() {
      if (this._page !== "list" || !this._key) return null;
      if (this._key === "new") return this._t("newGuest");
      return this._data?.guests.find((g) => g.id === this._key)?.name || this._form?.originalName || "…";
    }

    _render() {
      if (!this._hass) return;
      const sub = this._subName;
      const key = [this._page, !!this._narrow, this._lang, this._key, sub, this._view].join("|");
      if (key !== this._frameKey) {
        this._frameKey = key;
        this._frame(sub);
      }
      this._update();
    }

    // The parts that stay while a page is open: Home Assistant's frame with the
    // areas as tabs (a guest: back arrow and name), the pages of the area (a guest:
    // its views), the sheet and the save button
    _frame(sub) {
      const area = areaOf(this._page);
      const tabs = sub !== null
        ? this._tabGroup("views", GUEST_VIEWS, this._view)
        : area[3].length > 1 ? this._tabGroup("subtabs", area[3], this._page) : "";
      this.shadowRoot.innerHTML = `
        <style>${STYLE}</style>
        <hass-tabs-subpage id="frame">
          ${sub !== null ? `<div slot="header" class="subname">${esc(sub)}</div>` : ""}
          <div slot="toolbar-icon" class="actions"><span class="stamp" id="stamp"></span>
            <ha-icon-button id="refresh" data-act="refresh" label="${esc(this._t("refresh"))}" path="${MDI.refresh}"></ha-icon-button>
            <ha-icon-button id="integration" data-act="integration" label="${esc(this._t("integration"))}" path="${MDI.integration}"></ha-icon-button></div>
          <div class="page${this._narrow ? " narrow" : ""}">${tabs}<div class="sheet" id="sheet"></div></div>
          <ha-button slot="fab" id="save" size="l" data-act="save" hidden><ha-svg-icon slot="start" path="${MDI.save}"></ha-svg-icon>${esc(this._t("save"))}</ha-button>
        </hass-tabs-subpage>`;
      const frame = this.shadowRoot.getElementById("frame");
      frame.hass = this._hass;
      frame.narrow = !!this._narrow;
      frame.tabs = sub !== null ? [] : AREAS.map(([id, ic, label]) => ({ path: `${PANEL_PATH}/${id}`, name: this._t(label), iconPath: MDI[ic] }));
      frame.mainPage = sub === null;
      frame.backCallback = sub !== null ? () => this._act("back") : undefined;
      frame.route = this._route || { prefix: PANEL_PATH, path: `/${area[0]}/${this._page}` };
      this._sheetHtml = null;
    }

    _update() {
      const root = this.shadowRoot;
      const sheet = root.getElementById("sheet");
      if (sheet && !this._typing()) {
        this._forms = {};
        this._hid = 0;
        const html = this._sheet();
        if (html !== this._sheetHtml) {
          this._sheetHtml = html;
          sheet.innerHTML = html;
          this._hydrate(sheet);
        }
        this._redraw = false;
      }
      // The save button: only while something differs from what is saved
      const fab = root.getElementById("save");
      if (fab) {
        const show = this._page === "list" ? !!this._key && this._guestDirty
          : ["residents", "rooms", "timings"].includes(this._page) && this._settingsDirty;
        fab.hidden = !show;
        fab.disabled = !!this._busy;
        root.getElementById("frame").hasFab = show;
      }
      const stamp = root.getElementById("stamp");
      if (stamp) {
        stamp.textContent = this._stamp
          ? this._t("asOf", { time: this._stamp.toLocaleTimeString(this._lang, { hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }) })
          : "";
      }
      root.getElementById("refresh")?.classList.toggle("loading", !!this._loading);
    }

    // The sheet of the page in this._page
    _sheet() {
      const note = this._note ? this._errHtml(this._note) : "";
      if (!this._data) {
        return note + (this._loadError ? this._errHtml(this._loadError) : `<div class="loading-sheet"><ha-spinner></ha-spinner></div>`);
      }
      const page = {
        list: () => (this._key ? this._guestSheet() : this._listSheet()),
        overview: () => this._overviewSheet(),
        residents: () => this._residentsSheet(),
        rooms: () => this._roomsSheet(),
        timings: () => this._timingsSheet(),
      }[this._page];
      return note + page();
    }

    // ---- Guests ----

    _listSheet() {
      const data = this._data;
      const items = data.guests.map((guest) => {
        const color = STATUS_COLOR[guest.state.status] ?? STATUS_COLOR.away;
        const visit = guest.visit_minutes === null ? this._t("unlimited") : this._minutesText(guest.visit_minutes);
        const rooms = guest.all_rooms ? this._t("allRooms") : this._rooms(guest.rooms);
        const lead = guest.picture
          ? `<img class="lead photo" alt="" src="${esc(pictureUrl(guest.picture))}">`
          : `<span class="lead" style="color:${color};background:color-mix(in srgb, ${color} 15%, transparent)">${icon(guest.state.status in STATUS_COLOR ? guest.state.status : "away")}</span>`;
        const lock = guest.approval.kind === "off"
          ? ""
          : `<ha-icon-button data-act="lock" data-key="${esc(guest.id)}" label="${esc(this._t("lock"))}" path="${MDI.lock}"></ha-icon-button>`;
        return `<div class="item" role="button" tabindex="0" data-act="open" data-key="${esc(guest.id)}">${lead}` +
          `<span class="text"><span class="headline">${esc(guest.name)} · ${esc(this._statusText(guest))}</span>` +
          `<span class="supporting">${esc(this._approvalText(guest))}</span>` +
          `<span class="supporting">${esc(rooms)} · ${esc(visit)}</span></span>${lock}<span class="next">${icon("chevron")}</span></div>`;
      }).join("");
      const empty = `<div class="empty">${esc(this._t("noGuests"))}${this._help(this._t("noGuestsHelp"))}</div>`;
      const add = this._btn("open", this._t("addGuest"), { kind: "filled", data: ' id="add" data-key="new"' });
      return this._confirmHtml("lock") + this._lockAlert() +
        this._card(this._t("guests"), items || empty, { cls: "list", actions: add });
    }

    // The room lock in one line, the why behind its (i)
    _lockAlert() {
      const data = this._data;
      if (!data.settings.rooms.length) return "";
      return data.lock.active
        ? this._alert("info", this._t("lockActive", { locked: this._rooms(data.lock.locked_rooms) }),
          this._t("lockActiveHelp", { free: this._rooms(data.lock.free_rooms) }))
        : this._alert("info", this._t("lockOff"), this._t("lockOffHelp"));
    }

    // A guest: its views as tabs, one save button for all of them
    _guestSheet() {
      const f = this._guestForm();
      if (!f) return this._errHtml(errorText(this._texts, { code: "not_found" }));
      const view = {
        details: () => this._detailsView(f),
        approval: () => this._approvalView(f),
        rooms: () => this._roomsView(f),
        log: () => this._logView(f),
      }[this._view];
      return view();
    }

    _detailsView(f) {
      const rows =
        this._row("g-name", "name", { text: {} }, f.main.name, (v) => { f.main = { ...f.main, name: v ?? "" }; this._update(); }) +
        this._row("g-trackers", "trackers", { entity: { multiple: true, filter: { domain: "device_tracker" } } }, f.main.trackers,
          (v) => { f.main = { ...f.main, trackers: v ?? [] }; this._update(); });
      const avatar = f.media.picture
        ? `<img class="avatar" alt="" src="${esc(pictureUrl(f.media.picture))}">`
        : `<span class="avatar">${icon("account")}</span>`;
      const media = `<div class="media">${avatar}<div class="media-actions">` +
        `<input type="file" id="photo-file" accept="image/png,image/jpeg,image/gif" hidden>` +
        this._btn("photo-choose", this._t("choosePhoto")) +
        (f.media.picture ? this._btn("photo-remove", this._t("removePhoto")) : "") + `</div></div>` +
        this._row("g-note", "note", { text: { multiline: true } }, f.media.note, (v) => { f.media = { ...f.media, note: v ?? "" }; this._update(); });
      const del = f.id
        ? `<ha-card><div class="card-actions solo">${this._btn("delete", this._t("deleteGuest"), { kind: "danger" })}</div></ha-card>`
        : "";
      return this._confirmHtml("delete") +
        this._card("", rows, { cls: "settings" }) +
        this._card(this._t("mediaSection"), media, { cls: "settings", help: this._t("photoHelp") }) + del;
    }

    _approvalView(f) {
      const kind = f.approval.kind;
      const withEnd = kind === "once" || kind === "until";
      const set = (name, structural = false) => (v) => {
        f.approval = { ...f.approval, [name]: v };
        if (structural) this._redraw = true;
        this._update();
      };
      let rows = this._row("g-kind", "kind", { select: { mode: "dropdown", options: KINDS.map((k) => ({ value: k, label: this._t(`kind_${k}`) })) } },
        kind, set("kind", true), { kind: "required" });
      if (withEnd) rows += this._row("g-until", "until", { datetime: {} }, f.approval.until, set("until"));
      if (kind !== "off") rows += this._row("g-grace", "grace", null, f.approval.grace, set("grace"), { kind: "num", unit: this._t("unitMin") });
      let out = this._card(this._t("approvalSection"), rows, { cls: "settings" });
      if (kind === "until" || kind === "permanent") {
        const entries = f.windows.map((w, n) => `<div class="entry">${this._formSlot(`g-window-${n}`, [
          {
            name: "weekdays",
            required: true,
            selector: { select: { multiple: true, mode: "dropdown", options: this._t("weekdays").map((d, i) => ({ value: String(i), label: d })) } },
          },
          {
            type: "grid",
            name: "",
            schema: [
              { name: "start", required: true, selector: { time: { no_second: true } } },
              { name: "end", required: true, selector: { time: { no_second: true } } },
            ],
          },
        ], w, (value) => { f.windows[n] = value; this._update(); })}` +
          `<ha-icon-button data-act="window-remove" data-key="${n}" label="${esc(this._t("removeWindow"))}" path="${MDI.delete}"></ha-icon-button></div>`).join("");
        out += this._card(this._t("windows"), entries, { help: this._t("windowsHelp"), actions: this._btn("window-add", this._t("addWindow")) });
      }
      return out;
    }

    _roomsView(f) {
      const configured = this._data.settings.rooms.map((r) => r.area_id);
      const set = (name, structural = false) => (v) => {
        f.rooms = { ...f.rooms, [name]: v };
        if (structural) this._redraw = true;
        this._update();
      };
      let rows = "";
      if (configured.length) {
        rows += this._row("g-all", "all_rooms", { boolean: {} }, !!f.rooms.all_rooms, set("all_rooms", true), { kind: "bool" });
        if (!f.rooms.all_rooms) {
          rows += this._row("g-rooms", "rooms", { select: { multiple: true, mode: "list", options: configured.map((a) => ({ value: a, label: this._areaName(a) })) } },
            f.rooms.rooms, set("rooms"));
        }
      }
      rows += this._row("g-unlimited", "unlimited", { boolean: {} }, !!f.rooms.unlimited, set("unlimited", true), { kind: "bool" });
      if (!f.rooms.unlimited) {
        rows += this._row("g-visit", "visit_minutes", null, f.rooms.visit_minutes, set("visit_minutes"), { kind: "num", unit: this._t("unitMin") });
      }
      const none = configured.length ? "" : this._alert("info", this._t("noRooms"), this._t("roomsHelp"),
        this._btn("go", this._t("setUpRooms"), { data: ' data-key="setup/rooms"' }));
      return none + this._card(this._t("roomsSection"), rows, { cls: "settings" });
    }

    _logView(f) {
      const settings = this._data.settings;
      const row = this._row("g-log", "log_visits", { boolean: {} }, !!f.log.log_visits, (v) => {
        f.log = { log_visits: !!v };
        this._redraw = true;
        this._update();
      }, { kind: "bool", values: { grid: this._num(settings.log_grid_minutes), days: this._num(settings.log_keep_days), months: this._num(settings.log_keep_months) } });
      const guest = f.id ? this._data.guests.find((g) => g.id === f.id) : null;
      let body = "";
      // Loaded for this guest only, and again after every change
      const log = guest && f.wasLogging ? this._log(guest.id) : null;
      if (log && !f.log.log_visits && log.visits.length) body += this._alert("warning", this._t("logOffNote"));
      if (log && f.log.log_visits) {
        const lines = [];
        if (guest.state.counting && guest.state.arrived) {
          const since = new Date(guest.state.arrived);
          // On the grid of the log, as the finished visit will be
          const grid = (settings.log_grid_minutes || 15) * 60000;
          since.setTime(Math.round(since.getTime() / grid) * grid);
          lines.push(this._t("logRunning", { time: since.toLocaleString(this._lang, { dateStyle: "short", timeStyle: "short" }) }));
        }
        const [year, month] = log.this_month.split("-").map(Number);
        const last = month === 1 ? `${year - 1}-12` : `${year}-${pad(month - 1)}`;
        for (const [key, text] of [[log.this_month, "logMonth"], [last, "logLastMonth"]]) {
          const total = log.months[key] ?? { visits: 0, minutes: 0 };
          const visits = total.visits === 1 ? this._t("visitOne") : this._t("visitMany", { count: this._num(total.visits) });
          lines.push(this._t(text, { visits, hours: this._hours(total.minutes) }));
        }
        body += lines.map((line) => `<div class="line">${esc(line)}</div>`).join("");
        const visits = log.visits.slice(0, 10).map((visit) => {
          const start = new Date(visit.start);
          const end = new Date(start.getTime() + visit.minutes * 60000);
          const when = `${start.toLocaleDateString(this._lang, { weekday: "short", day: "numeric", month: "numeric" })}, ` +
            `${start.toLocaleTimeString(this._lang, { timeStyle: "short" })}–${end.toLocaleTimeString(this._lang, { timeStyle: "short" })}`;
          return `<div class="visit"><span>${esc(when)}</span><span>${esc(this._hours(visit.minutes))} h</span></div>`;
        }).join("");
        body += `<div class="visits">${visits || `<div class="line">${esc(this._t("logNone"))}</div>`}</div>`;
        body += `<div class="log-actions">${this._btn("log-export", this._t("logExport"), { disabled: !log.visits.length })}` +
          `${this._btn("log-delete", this._t("logDelete"), { kind: "danger", disabled: !log.visits.length && !Object.keys(log.months).length })}</div>`;
      }
      return this._confirmHtml("logDelete") + this._card(this._t("logSection"), row, { cls: "settings" }) +
        (body ? this._card("", body) : "");
    }

    // ---- Setup ----

    _overviewSheet() {
      const data = this._data;
      const s = data.settings;
      const residents = s.residents.map((id) => this._entityName(id)).join(", ");
      const rooms = this._rooms(s.rooms.map((r) => r.area_id));
      const steps = [
        ["setup/residents", this._t("stepResidents"), s.residents.length > 0, residents || this._t("noneYet")],
        ["setup/rooms", this._t("stepRooms"), s.rooms.length > 0, s.rooms.length ? rooms : this._t("noneYet")],
        [data.guests.length ? "guests/list" : "guests/list?key=new", this._t("stepGuests"), data.guests.length > 0,
          data.guests.length ? this._t("guestCount", { n: this._num(data.guests.length) }) : this._t("noneYet")],
      ];
      const next = steps.find((x) => !x[2]);
      const items = steps.map(([path, title, done, sub], i) => {
        const state = this._t(done ? "stepDone" : "stepOpen");
        return `<div class="item" role="button" tabindex="0" data-act="go" data-key="${esc(path)}">` +
          `<span class="lead step${done ? " done" : ""}" aria-label="${esc(state)}" title="${esc(state)}">${done ? icon("check") : `<b>${i + 1}</b>`}</span>` +
          `<span class="text"><span class="headline">${esc(title)}</span><span class="supporting">${esc(sub)}</span></span>` +
          `<span class="next">${icon("chevron")}</span></div>`;
      }).join("");
      const actions = next ? this._btn("go", this._t("next"), { kind: "filled", data: ` id="next" data-key="${esc(next[0])}"` }) : "";
      const about = data.about;
      const line = about?.version
        ? this._t(about.commit ? "aboutCommit" : "about", { version: about.version, commit: about.commit || "" })
        : "";
      return this._card(this._t("setupTitle"), items, { cls: "list", help: this._t("setupHelp"), actions }) +
        `<div class="about">${esc(line)}</div>`;
    }

    _residentsSheet() {
      const s = this._settingsNow();
      return this._card(this._t("pageResidents"),
        this._row("s-residents", "residents", { entity: { multiple: true, filter: { domain: "person" } } }, s.residents,
          (v) => { this._setSetting({ residents: v ?? [] }); this._update(); }),
        { cls: "settings" });
    }

    _roomsSheet() {
      const s = this._settingsNow();
      const entries = s.rooms.map((room, i) => `<div class="entry">${this._formSlot(`s-room-${i}`, [
        {
          type: "grid",
          name: "",
          schema: [
            { name: "area", required: true, selector: { area: {} } },
            { name: "door", required: true, selector: { entity: { filter: { domain: "binary_sensor" } } } },
          ],
        },
      ], { area: room.area_id || null, door: room.door || null }, (value) => {
        const rooms = this._settingsNow().rooms.map((r) => ({ ...r }));
        rooms[i] = { area_id: value.area || "", door: value.door || "" };
        this._setSetting({ rooms });
        this._update();
      })}<ha-icon-button data-act="room-remove" data-key="${i}" label="${esc(this._t("removeRoom"))}" path="${MDI.delete}"></ha-icon-button></div>`).join("");
      const empty = s.rooms.length ? "" : `<div class="line">${esc(this._t("noRooms"))}</div>`;
      return this._card(this._t("lockableRooms"), empty + entries, { help: this._t("roomsHelp"), actions: this._btn("room-add", this._t("addRoom")) });
    }

    _timingsSheet() {
      const s = this._settingsNow();
      const set = (name) => (v) => { this._setSetting({ [name]: v }); this._update(); };
      const min = { kind: "num", unit: this._t("unitMin") };
      return this._card(this._t("timingsSection"),
        this._row("s-resume", "resume_minutes", null, s.resume_minutes, set("resume_minutes"), min), { cls: "settings" }) +
        this._card(this._t("logSection"),
          this._row("s-grid", "log_grid_minutes", null, s.log_grid_minutes, set("log_grid_minutes"), min) +
          this._row("s-days", "log_keep_days", null, s.log_keep_days, set("log_keep_days"), { kind: "num", unit: this._t("unitDays") }) +
          this._row("s-months", "log_keep_months", null, s.log_keep_months, set("log_keep_months"), { kind: "num", unit: this._t("unitMonths") }),
          { cls: "settings" });
    }

    // ---- Actions ----

    _bindOnce() {
      const root = this.shadowRoot;
      root.addEventListener("click", (e) => {
        const el = e.target.closest?.("[data-act]");
        if (el && !el.disabled) this._act(el.dataset.act, el);
      });
      // A list row that opens something does so with Enter or Space, as a button would
      root.addEventListener("keydown", (e) => {
        const item = e.target.closest?.(".item[data-act]");
        if (!item || e.target !== item || (e.key !== "Enter" && e.key !== " ")) return;
        e.preventDefault();
        this._act(item.dataset.act, item);
      });
      root.addEventListener("change", (e) => {
        if (e.target.id === "photo-file") this._photoChosen(e.target);
      });
      // Home Assistant's tabs: a page of the area, a view of the guest
      root.addEventListener("wa-tab-show", (e) => {
        const name = e.detail?.name;
        const group = e.target?.id;
        if (!name) return;
        if (group === "subtabs" && name !== this._page) navigate(pagePath(name));
        else if (group === "views" && name !== this._view && this._key) {
          const view = name === "details" ? "" : `&view=${name}`;
          navigate(`${pagePath("list")}?key=${encodeURIComponent(this._key)}${view}`, true);
        }
      });
    }

    async _act(act, el = { dataset: {} }) {
      const key = el.dataset?.key;
      const f = this._form;
      switch (act) {
        case "refresh":
          this._refresh();
          return;
        case "integration":
          navigate(INTEGRATION_PATH);
          return;
        case "open":
          navigate(`${pagePath("list")}?key=${encodeURIComponent(key)}`);
          return;
        case "go":
          navigate(`${PANEL_PATH}/${key}`);
          return;
        case "back":
          navigate(pagePath("list"), true);
          return;
        case "lock": {
          const guest = this._data.guests.find((g) => g.id === key);
          if (guest) this._confirm = { action: "lock", id: guest.id, name: guest.name };
          break;
        }
        case "delete":
          this._confirm = { action: "delete", id: f.id, name: f.originalName };
          break;
        case "log-delete":
          this._confirm = { action: "logDelete", id: f.id, name: f.originalName };
          break;
        case "confirm-cancel":
          this._confirm = null;
          break;
        case "confirm-ok":
          this._runConfirm();
          return;
        case "log-export": {
          const guest = this._data.guests.find((g) => g.id === f?.id);
          const log = guest && this._logs[guest.id]?.log;
          if (log) this._exportCsv(guest, log);
          return;
        }
        case "photo-choose":
          this.shadowRoot.getElementById("photo-file")?.click();
          return;
        case "photo-remove":
          f.media = { ...f.media, picture: null };
          break;
        case "window-add":
          f.windows.push({ weekdays: ["0", "1", "2", "3", "4"], start: "08:00:00", end: "18:00:00" });
          break;
        case "window-remove":
          f.windows.splice(Number(key), 1);
          break;
        case "room-add":
          this._setSetting({ rooms: [...this._settingsNow().rooms, { area_id: "", door: "" }] });
          break;
        case "room-remove":
          this._setSetting({ rooms: this._settingsNow().rooms.filter((_, i) => i !== Number(key)) });
          break;
        case "save":
          if (this._page === "list") this._saveGuest();
          else this._saveSettings();
          return;
        default:
          return;
      }
      this._redraw = true;
      this._render();
    }

    async _runConfirm() {
      const c = this._confirm;
      this._confirm = null;
      if (!c) return;
      try {
        if (c.action === "lock") await this._call({ type: `${DOMAIN}/lock_guest`, guest_id: c.id });
        else if (c.action === "logDelete") await this._call({ type: `${DOMAIN}/delete_visits`, guest_id: c.id });
        else {
          await this._call({ type: `${DOMAIN}/delete_guest`, guest_id: c.id });
          this._dropUploads(this._form);
          this._form = null;
          navigate(pagePath("list"), true);
        }
      } catch {
        // Shown on the page
      }
    }

    // Delete the photos a guest's draft uploaded but did not save; Guest Access also
    // deletes them itself after a while, this only does it at once
    _dropUploads(f, kept = null) {
      if (!f?.uploaded?.length) return;
      for (const id of f.uploaded) {
        if (id !== kept) this._hass.callWS({ type: "image/delete", image_id: id }).catch(() => {});
      }
      f.uploaded = [];
    }

    async _photoChosen(input) {
      const f = this._form;
      const file = input.files?.[0];
      if (!file || !f) return;
      try {
        const id = await this._upload(file);
        f.uploaded.push(id);
        if (this._form !== f) {
          // The guest was closed while the photo was uploading
          this._dropUploads(f, f.saved ? f.media.picture : null);
          return;
        }
        f.media = { ...f.media, picture: id };
        this._note = null;
      } catch (err) {
        this._note = errorText(this._texts, err);
      }
      this._redraw = true;
      this._render();
    }

    // Upload a photo through Guest Access, into Home Assistant's images; its ID.
    // The upload is HTTP: its status gives the kind of error, as the WebSocket's codes do
    async _upload(file) {
      const form = new FormData();
      form.append("file", file);
      const response = await this._hass.fetchWithAuth(`/api/${DOMAIN}/picture`, { method: "POST", body: form });
      if (!response.ok) {
        const body = await response.text();
        let message = body;
        try {
          message = JSON.parse(body).message || body;
        } catch {
          // Not JSON: the text as it is
        }
        throw { code: HTTP_CODES[response.status], message };
      }
      return (await response.json()).id;
    }

    _exportCsv(guest, log) {
      const rows = [this._t("csvHeader")];
      for (const visit of [...log.visits].reverse()) {
        const start = new Date(visit.start);
        const end = new Date(start.getTime() + visit.minutes * 60000);
        const time = (d) => d.toLocaleTimeString(this._lang, { hour: "2-digit", minute: "2-digit" });
        rows.push([start.toLocaleDateString(this._lang), time(start), time(end), this._hours(visit.minutes)].join(";"));
      }
      const blob = new Blob([`﻿${rows.join("\r\n")}\r\n`], { type: "text/csv;charset=utf-8" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      const safe = guest.name.replace(/[^\p{L}\p{N}_-]+/gu, "-");
      link.download = `guest-access-${safe}-${new Date().toISOString().slice(0, 10)}.csv`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    }

    async _saveGuest() {
      const f = this._form;
      if (!f || f.saving) return;
      const full = this._guestMessage(f);
      const message = { ...full };
      if (f.media.picture === f.originalPicture) delete message.picture;
      if (f.id) message.guest_id = f.id;
      f.saving = true;
      let result;
      try {
        result = await this._call(message);
      } catch {
        // Shown on the page
      }
      f.saving = false;
      if (!result) return;
      // What was sent is what is saved now; the photos not sent go
      f.base = JSON.stringify(full);
      f.saved = true;
      this._dropUploads(f, full.picture);
      f.originalPicture = full.picture;
      f.originalName = full.name;
      f.wasLogging = full.log_visits;
      if (!f.id) {
        // A new guest: its own address from now on
        f.id = result.guest_id;
        f.key = result.guest_id;
        if (this._form === f) {
          const view = this._view === "details" ? "" : `&view=${this._view}`;
          navigate(`${pagePath("list")}?key=${encodeURIComponent(f.id)}${view}`, true);
        }
      }
      this._redraw = true;
      this._render();
    }

    async _saveSettings() {
      if (!this._settings) return;
      const sent = this._settings;
      try {
        await this._call(this._settingsMessage(sent));
      } catch {
        return;
      }
      if (this._settings === sent) this._settings = null;
      this._redraw = true;
      this._render();
    }
  }

  // The number helpers, for the integration's own code
  GuestAccessPanel.numbers = { formatNumber, fieldNumber, numOrNull };

  customElements.define("guest-access-panel", GuestAccessPanel);
}

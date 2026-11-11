// Guest Access panel: the page in the sidebar where administrators add guests,
// approve and lock them, and set the residents and the lockable rooms. Every
// change goes to the integration over the WebSocket API; the list follows the
// integration's state live.
//
// The page is built from Home Assistant's own elements (cards, buttons, alerts
// and ha-form with selectors), so it looks and behaves like the rest of the UI.
// The header is one row, as on every page of Nico's apps and integrations: the
// integration's icon and name with the two tabs (Guests, Rooms; the tab is in
// the URL), then stamp, refresh and settings. At phone width the tabs sit at
// the bottom, as in Network Plus. An edit opens as a subpage with a back arrow.

if (!customElements.get("guest-access-panel")) {
  const TEXTS = {
    en: {
      title: "Guest Access",
      tabGuests: "Guests",
      tabRooms: "Rooms",
      guests: "Guests",
      addGuest: "Add guest",
      noGuests: "No guests yet. A guest counts as home only with an approval.",
      settings: "Residents and rooms",
      edit: "Edit",
      lock: "Lock",
      lockConfirm: "Lock {name}? The guest no longer counts as home until approved again.",
      delete: "Delete",
      deleteConfirm: "Delete {name} with the device and its entities?",
      confirm: "Confirm",
      save: "Save",
      cancel: "Cancel",
      back: "Back",
      field_name: "Name",
      field_trackers: "Trackers",
      field_kind: "Approval",
      field_until: "Until",
      field_grace: "Grace time",
      field_all_rooms: "All rooms",
      field_rooms: "Rooms on top of the living area",
      field_visit: "Time per visit",
      field_residents: "Residents",
      field_area: "Area",
      field_door: "Door contact",
      field_weekdays: "Weekdays",
      field_start: "From",
      field_end: "To",
      help_trackers: "The guest is home when one of them is home.",
      help_grace: "A return within this time continues the visit; afterwards a once approval ends.",
      help_residents: "The room lock applies only while none of them is home.",
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
      allRooms: "all rooms",
      unlimited: "unlimited",
      minutes: "{n} min",
      status_counting: "Counts as home",
      status_time_up: "Time up",
      status_approval_expired: "Approval expired",
      status_not_approved: "Home without approval",
      status_resuming: "Waiting after restart",
      status_away: "Away",
      status_inactive: "No approval",
      visitEnds: "until {time}",
      residents: "Residents",
      lockActive: "Room lock active: only guests are home. Locked: {locked}. Free: {free}.",
      lockOff: "Room lock off: a resident is home or no guest counts.",
      none: "none",
      error: "Error: {message}",
      weekdays: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
      weekdaysShort: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
      field_log_visits: "Keep a visit log",
      help_log_visits: "Date, start and length of each visit on a {grid}-minute grid; single visits for {days} days, monthly totals for {months} months. Switched off, the log so far is deleted.",
      field_unlimited: "Unlimited time per visit",
      field_visit_minutes: "Time per visit",
      timingsSection: "Timings",
      field_resume_minutes: "Time to be seen again after a restart",
      help_resume_minutes: "A guest who counted before a restart continues the visit when a tracker reports home within this time.",
      field_log_grid_minutes: "Grid of the visit log",
      field_log_keep_days: "Keep single visits",
      field_log_keep_months: "Keep monthly totals",
      logSection: "Visit log",
      mediaSection: "Photo and note",
      photoHelp: "Shown on dashboards, as a person's picture is.",
      choosePhoto: "Choose photo",
      removePhoto: "Remove photo",
      field_note: "Note",
      help_note: "Only administrators see it, here on this page.",
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
      about: "Guest Access {version}",
      aboutCommit: "Guest Access {version} · commit {commit}",
      asOf: "As of {time}",
      refresh: "Refresh",
      integrationSettings: "Settings",
    },
    de: {
      title: "Guest Access",
      tabGuests: "Gäste",
      tabRooms: "Räume",
      guests: "Gäste",
      addGuest: "Gast hinzufügen",
      noGuests: "Noch keine Gäste. Ein Gast zählt nur mit Freigabe als daheim.",
      settings: "Bewohner und Räume",
      edit: "Bearbeiten",
      lock: "Sperren",
      lockConfirm: "{name} sperren? Der Gast zählt dann nicht mehr als zuhause, bis er wieder freigegeben wird.",
      delete: "Löschen",
      deleteConfirm: "{name} mit Gerät und Entitäten löschen?",
      confirm: "Bestätigen",
      save: "Speichern",
      cancel: "Abbrechen",
      back: "Zurück",
      field_name: "Name",
      field_trackers: "Tracker",
      field_kind: "Freigabe",
      field_until: "Bis",
      field_grace: "Kulanzzeit",
      field_all_rooms: "Alle Räume",
      field_rooms: "Räume zusätzlich zum Wohnbereich",
      field_visit: "Dauer je Besuch",
      field_residents: "Bewohner",
      field_area: "Bereich",
      field_door: "Türkontakt",
      field_weekdays: "Wochentage",
      field_start: "Von",
      field_end: "Bis",
      help_trackers: "Der Gast ist daheim, sobald einer davon daheim ist.",
      help_grace: "Wer in dieser Zeit zurückkommt, setzt den Besuch fort; danach endet eine einmalige Freigabe.",
      help_residents: "Die Raumsperre gilt nur, solange keiner von ihnen daheim ist.",
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
      allRooms: "alle Räume",
      unlimited: "unbegrenzt",
      minutes: "{n} min",
      status_counting: "Zählt als daheim",
      status_time_up: "Zeit um",
      status_approval_expired: "Freigabe abgelaufen",
      status_not_approved: "Daheim ohne Freigabe",
      status_resuming: "Wartet nach Neustart",
      status_away: "Weg",
      status_inactive: "Ohne Freigabe",
      visitEnds: "bis {time}",
      residents: "Bewohner",
      lockActive: "Raumsperre aktiv: nur Gäste daheim. Gesperrt: {locked}. Frei: {free}.",
      lockOff: "Raumsperre aus: ein Bewohner ist daheim oder kein Gast zählt.",
      none: "keine",
      error: "Fehler: {message}",
      weekdays: ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
      weekdaysShort: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
      field_log_visits: "Besuchsprotokoll führen",
      help_log_visits: "Datum, Beginn und Dauer je Besuch, auf {grid} Minuten gerundet; einzelne Besuche {days} Tage, Monatssummen {months} Monate. Ausgeschaltet wird das bisherige Protokoll gelöscht.",
      field_unlimited: "Unbegrenzte Dauer je Besuch",
      field_visit_minutes: "Dauer je Besuch",
      timingsSection: "Zeiten",
      field_resume_minutes: "Wiedererkennung nach Neustart",
      help_resume_minutes: "Ein Gast, der vor einem Neustart zählte, setzt den Besuch fort, wenn ein Tracker in dieser Zeit daheim meldet.",
      field_log_grid_minutes: "Raster des Besuchsprotokolls",
      field_log_keep_days: "Einzelne Besuche aufbewahren",
      field_log_keep_months: "Monatssummen aufbewahren",
      logSection: "Besuchsprotokoll",
      mediaSection: "Foto und Notiz",
      photoHelp: "Erscheint auf Dashboards, wie das Bild einer Person.",
      choosePhoto: "Foto wählen",
      removePhoto: "Foto entfernen",
      field_note: "Notiz",
      help_note: "Sehen nur Administratoren, hier auf dieser Seite.",
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
      about: "Guest Access {version}",
      aboutCommit: "Guest Access {version} · Commit {commit}",
      asOf: "Stand {time}",
      refresh: "Aktualisieren",
      integrationSettings: "Einstellungen",
    },
  };
  const KINDS = ["off", "once", "until", "permanent"];
  // Home Assistant's page of the integration, behind the settings button
  const INTEGRATION_PAGE = "/config/integrations/integration/guest_access";
  // The page in the sidebar; a tab adds its name to the path
  const PANEL_PATH = "/guest-access";
  // Tab, icon at phone width, text
  const TABS = [
    ["guests", "mdi:account-multiple", "tabGuests"],
    ["rooms", "mdi:door-closed-lock", "tabRooms"],
  ];
  // The integration's own icon (brand/icon.png), as Home Assistant serves it to the
  // signed-in browser: with the brands token, which Home Assistant renews every 30 min
  const BRAND_ICON = "/api/brands/integration/guest_access/icon.png";
  // A failed subscription, the entry still loading say, is tried again after this time
  const RETRY_MS = 5000;
  // Icon and colour per status, as the status sensor shows it
  const STATUS = {
    counting: ["mdi:account-check", "var(--success-color, #43a047)"],
    time_up: ["mdi:account-clock", "var(--warning-color, #ffa600)"],
    approval_expired: ["mdi:account-alert", "var(--warning-color, #ffa600)"],
    not_approved: ["mdi:account-cancel", "var(--warning-color, #ffa600)"],
    resuming: ["mdi:account-sync", "var(--info-color, #039be5)"],
    away: ["mdi:account-outline", "var(--secondary-text-color, #727272)"],
    inactive: ["mdi:account-lock-outline", "var(--disabled-text-color, #9e9e9e)"],
  };

  const esc = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
  const pad = (n) => String(n).padStart(2, "0");
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

  const STYLE = `
    :host { display: block; height: 100vh; height: 100dvh; background: var(--primary-background-color);
      color: var(--primary-text-color); }
    * { box-sizing: border-box; }
    .app { display: flex; flex-direction: column; height: 100%; }
    /* One header row like the settings and other panels, in the sidebar's colour with a
       line: menu or back arrow, icon, name, tabs; stamp, refresh and settings at the end */
    .toolbar { display: flex; align-items: center; flex: none; height: var(--header-height, 56px);
      padding: 0 12px; background: var(--sidebar-background-color, var(--card-background-color));
      color: var(--sidebar-text-color, var(--primary-text-color)); border-bottom: 1px solid var(--divider-color); }
    .toolbar > ha-menu-button, .toolbar > #back { color: var(--sidebar-icon-color, var(--secondary-text-color));
      flex: none; }
    .brand { width: 24px; height: 24px; flex: none; margin-inline-start: 12px; }
    .main-title { font-size: 20px; font-weight: 400; line-height: 32px; margin-inline-start: 12px;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
    .tabs { display: flex; height: 100%; margin-inline-start: 24px; overflow-x: auto; scrollbar-width: none;
      flex: none; }
    .tab { display: flex; align-items: center; justify-content: center; height: 100%; padding: 0 20px;
      position: relative; color: var(--sidebar-text-color, var(--primary-text-color)); text-decoration: none;
      font-weight: 500; white-space: nowrap; opacity: 0.8; }
    .tab:hover { background: color-mix(in srgb, var(--primary-text-color) 5%, transparent); }
    .tab.active { color: var(--primary-color); opacity: 1; }
    .tabs .tab.active::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 2px;
      background: var(--primary-color); }
    .tools { display: flex; align-items: center; gap: 4px; margin-inline-start: auto; padding-inline-start: 8px;
      flex: none; }
    .tools ha-icon-button { color: var(--sidebar-icon-color, var(--secondary-text-color)); }
    .stamp { color: var(--secondary-text-color); font-size: var(--ha-font-size-m, 14px);
      white-space: nowrap; font-variant-numeric: tabular-nums; margin-inline-end: 4px; }
    /* At phone width the tabs are at the bottom, with icons, as in Network Plus */
    .bottom-tabs { display: flex; flex: none; justify-content: space-around;
      background: var(--sidebar-background-color, var(--card-background-color));
      border-top: 1px solid var(--divider-color); padding-bottom: env(safe-area-inset-bottom); }
    .bottom-tabs .tab { flex: 1 1 0; flex-direction: column; gap: 2px; height: 56px; padding: 6px 2px 4px;
      font-size: 11px; min-width: 0; }
    .bottom-tabs .tab span { overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
    .bottom-tabs .tab ha-icon { padding: 2px 12px; border-radius: 14px; box-sizing: content-box; }
    .bottom-tabs .tab.active ha-icon { background: color-mix(in srgb, var(--primary-color) 15%, transparent); }
    .scroller { flex: 1 1 auto; min-height: 0; overflow-y: auto; }
    #refresh.loading ha-icon { animation: spin 1s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .about { text-align: center; color: var(--secondary-text-color); font-size: var(--ha-font-size-s, 12px);
      padding: 8px 0 24px; }
    .visits { margin: 8px 0; }
    .visit { display: flex; justify-content: space-between; padding: 6px 0;
      border-top: 1px solid var(--divider-color); font-size: var(--ha-font-size-m, 14px); }
    .visit:first-child { border-top: none; }
    .log-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    .content { max-width: 860px; margin: 0 auto; padding: 16px; box-sizing: border-box;
      display: flex; flex-direction: column; gap: 16px; }
    ha-card { overflow: hidden; }
    .card-content { padding: 0 16px 16px; }
    .card-content.top { padding-top: 16px; }
    .card-content.list { padding: 0 0 8px; }
    .card-actions { display: flex; gap: 8px; justify-content: flex-end; align-items: center;
      padding: 8px 16px; border-top: 1px solid var(--divider-color); }
    .card-actions .spacer { flex: 1; }
    .item { display: flex; align-items: center; gap: 16px; padding: 8px 8px 8px 16px; min-height: 72px;
      box-sizing: border-box; cursor: pointer; }
    .item:hover { background: var(--secondary-background-color); }
    .item .icon { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center;
      justify-content: center; flex: none; }
    .item .icon ha-icon { --mdc-icon-size: 24px; }
    .item .photo { object-fit: cover; }
    .media { display: flex; align-items: center; gap: 16px; margin-bottom: 8px; flex-wrap: wrap; }
    .media .avatar { width: 96px; height: 96px; border-radius: 50%; flex: none; object-fit: cover;
      display: flex; align-items: center; justify-content: center;
      background: var(--secondary-background-color); color: var(--secondary-text-color); }
    .media .avatar ha-icon { --mdc-icon-size: 48px; }
    .media .media-actions { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; }
    .item .text { flex: 1; min-width: 0; }
    .item .headline { font-size: var(--ha-font-size-l, 16px); font-weight: var(--ha-font-weight-medium, 500);
      line-height: 24px; }
    .item .supporting { font-size: var(--ha-font-size-m, 14px); color: var(--secondary-text-color);
      line-height: 20px; }
    .item .chevron { color: var(--secondary-text-color); }
    .row { display: flex; align-items: center; gap: 16px; padding: 12px 16px; }
    .row .label { flex: none; width: 160px; color: var(--secondary-text-color); }
    .row .value { flex: 1; min-width: 0; }
    .empty { padding: 0 16px 8px; color: var(--secondary-text-color); }
    .note { color: var(--secondary-text-color); font-size: var(--ha-font-size-m, 14px); margin: 0 0 8px; }
    .entry { display: flex; align-items: flex-start; gap: 8px; padding: 8px 0;
      border-top: 1px solid var(--divider-color); }
    .entry:first-of-type { border-top: none; }
    .entry ha-form { flex: 1; min-width: 0; }
    .entry ha-icon-button { margin-top: 4px; color: var(--secondary-text-color); }
    ha-alert { display: block; }
    ha-alert ha-button { margin-inline-start: 8px; }
    @media (max-width: 600px) {
      .stamp { display: none; }
      .content { padding: 8px; gap: 8px; }
      .row { flex-direction: column; align-items: flex-start; gap: 2px; }
      .row .label { width: auto; }
    }
  `;

  class GuestAccessPanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._data = null;
      // What is being edited: null, {kind: "guest", ...} or {kind: "settings", ...}
      this._form = null;
      // A pending confirmation: {action: "lock" | "delete", id, name}
      this._confirm = null;
      this._error = "";
      this._tab = "guests";
      // The URL of the integration's icon, with the current brands token
      this._brand = "";
    }

    set hass(hass) {
      const first = !this._hass;
      this._hass = hass;
      if (first) {
        this._render();
        this._subscribe();
        this._brandToken();
      }
      for (const el of this.shadowRoot.querySelectorAll("ha-menu-button, ha-form")) el.hass = hass;
    }

    set narrow(narrow) {
      const changed = !!narrow !== !!this._narrow;
      this._narrow = narrow;
      const menu = this.shadowRoot.querySelector("ha-menu-button");
      if (menu) menu.narrow = narrow;
      // The tabs move between the header and the bottom
      if (changed && this._hass) this._render();
    }

    // The tab is the part of the path after the page: /guest-access/rooms
    set route(route) {
      const tab = (route?.path || "").split("/")[1] || "guests";
      const next = TABS.some(([id]) => id === tab) ? tab : "guests";
      if (next === this._tab) return;
      this._tab = next;
      this._confirm = null;
      if (this._hass) this._render();
    }

    // The brands token for the icon; fetched again on a refresh and when the icon fails
    async _brandToken() {
      try {
        const { token } = await this._hass.callWS({ type: "brands/access_token" });
        this._brand = `${BRAND_ICON}?token=${encodeURIComponent(token)}`;
      } catch {
        this._brand = "";
      }
      this._renderHeader();
    }

    _openTab(tab) {
      history.pushState(null, "", `${PANEL_PATH}/${tab}`);
      window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
    }

    disconnectedCallback() {
      clearTimeout(this._retry);
      // Leaving the page drops photos uploaded in an open form but not saved
      this._dropUploads(this._form);
      this._form = null;
      this._confirm = null;
      if (this._unsub) {
        this._unsub.then((unsub) => unsub()).catch(() => {});
        this._unsub = null;
      }
    }

    connectedCallback() {
      if (this._hass && !this._unsub) this._subscribe();
    }

    _t(key, values = {}) {
      const lang = (this._hass?.locale?.language || this._hass?.language || "en").startsWith("de")
        ? "de"
        : "en";
      let text = TEXTS[lang][key] ?? TEXTS.en[key] ?? key;
      if (typeof text === "string") {
        // A function as replacement keeps "$" in names as they are
        for (const [name, value] of Object.entries(values)) text = text.replace(`{${name}}`, () => value);
      }
      return text;
    }

    _subscribe() {
      this._unsub = this._hass.connection.subscribeMessage(
        (data) => {
          this._data = data;
          this._stamp = new Date();
          const refreshed = this._loading;
          this._loading = false;
          if (this._subscribeFailed) {
            // Loaded after all: the error of the failed attempt is gone
            this._subscribeFailed = false;
            this._error = "";
          }
          // An open form keeps what is being typed; only the list follows the state.
          // A refresh asked for redraws a form as well, from the values typed so far.
          if (!this._form || refreshed) this._render();
          else this._renderHeader();
        },
        { type: "guest_access/subscribe" },
      );
      const attempt = this._unsub;
      attempt.catch((err) => {
        this._loading = false;
        this._error = err.message || String(err);
        this._subscribeFailed = true;
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

    // Header: fetch the data again over the WebSocket, without reloading the page
    async _refresh() {
      if (this._loading || !this._hass) return;
      this._loading = true;
      this._renderHeader();
      clearTimeout(this._retry);
      const old = this._unsub;
      this._unsub = null;
      if (old) await old.then((unsub) => unsub()).catch(() => {});
      this._brandToken();
      if (this.isConnected && !this._unsub) this._subscribe();
      else this._loading = false;
      this._renderHeader();
    }

    // Header: Home Assistant's page of the integration, opened as its own links do
    _openIntegration() {
      history.pushState(null, "", INTEGRATION_PAGE);
      window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
    }

    _renderHeader() {
      const root = this.shadowRoot;
      const stamp = root.getElementById("stamp");
      if (stamp) {
        const d = this._stamp;
        stamp.textContent = d
          ? this._t("asOf", { time: `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}` })
          : "";
      }
      const brand = root.getElementById("brand");
      if (brand && this._brand && brand.getAttribute("src") !== this._brand) brand.src = this._brand;
      const refresh = root.getElementById("refresh");
      if (refresh) {
        refresh.classList.toggle("loading", !!this._loading);
        refresh.disabled = !!this._loading;
      }
    }

    async _call(message) {
      this._error = "";
      try {
        return await this._hass.callWS(message);
      } catch (err) {
        this._error = err.message || String(err);
        this._render();
        throw err;
      }
    }

    // Names and texts

    _areaName(areaId) {
      return this._hass.areas?.[areaId]?.name || areaId;
    }

    _entityName(entityId) {
      return this._hass.states[entityId]?.attributes?.friendly_name || entityId;
    }

    _time(iso) {
      return new Date(iso).toLocaleString(this._hass.locale?.language || undefined, {
        dateStyle: "short",
        timeStyle: "short",
      });
    }

    _rooms(ids) {
      return ids.map((id) => this._areaName(id)).join(", ") || this._t("none");
    }

    _approvalText(guest) {
      const a = guest.approval;
      let text = this._t(`kind_${a.kind}`);
      if (a.until) text += ` ${this._time(a.until)}`;
      const windows = a.windows.map(
        (w) =>
          `${w.weekdays.map((d) => this._t("weekdaysShort")[d]).join(", ")} ${withoutSeconds(w.start)}–${withoutSeconds(w.end)}`,
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

    // Layout: one header row, then a tab or a subpage with a form

    // The frame changes only between tabs, forms and widths, so a re-render of the
    // content keeps the scroll position
    _render() {
      const root = this.shadowRoot;
      const editing = !!this._form;
      const narrow = !!this._narrow;
      const mode = `${editing ? `${this._form.kind}:${this._form.id ?? ""}` : `tab:${this._tab}`}|${narrow}`;
      if (this._mode === mode && root.getElementById("content")) {
        this._renderHeader();
        this._renderContent(root.getElementById("content"));
        return;
      }
      this._mode = mode;
      const title = !editing
        ? this._t("title")
        : this._form.kind === "settings"
          ? this._t("settings")
          : this._form.id
            ? this._form.originalName
            : this._t("addGuest");
      const tabs = TABS.map(
        ([id, icon, label]) =>
          `<a class="tab${this._tab === id ? " active" : ""}" data-tab="${id}" href="${PANEL_PATH}/${id}">` +
          `${narrow ? `<ha-icon icon="${icon}"></ha-icon>` : ""}<span>${esc(this._t(label))}</span></a>`,
      ).join("");
      // A subpage has the back arrow in place of the menu and the icon, and no tabs
      root.innerHTML = `
        <style>${STYLE}</style>
        <div class="app${narrow ? " narrow" : ""}">
          <div class="toolbar">
            ${
              editing
                ? `<ha-icon-button id="back" label="${esc(this._t("back"))}"><ha-icon icon="mdi:arrow-left"></ha-icon></ha-icon-button>`
                : `<ha-menu-button></ha-menu-button><img class="brand" id="brand" alt="">`
            }
            <div class="main-title" id="title">${esc(title)}</div>
            ${editing || narrow ? "" : `<nav class="tabs" id="tabs">${tabs}</nav>`}
            <div class="tools" id="tools">
              <span class="stamp" id="stamp"></span>
              <ha-icon-button id="refresh" label="${esc(this._t("refresh"))}"><ha-icon icon="mdi:refresh"></ha-icon></ha-icon-button>
              <ha-icon-button id="integration" label="${esc(this._t("integrationSettings"))}"><ha-icon icon="mdi:cog-outline"></ha-icon></ha-icon-button>
            </div>
          </div>
          <div class="scroller"><div class="content" id="content"></div></div>
          ${!editing && narrow ? `<nav class="bottom-tabs" id="tabs">${tabs}</nav>` : ""}
        </div>`;
      const menu = root.querySelector("ha-menu-button");
      if (menu) {
        menu.hass = this._hass;
        menu.narrow = this._narrow;
      }
      // An icon with a token that ran out: fetch a new one, once per page view
      const brand = root.getElementById("brand");
      brand?.addEventListener(
        "error",
        () => {
          if (this._brand) this._brandToken();
        },
        { once: true },
      );
      for (const link of root.querySelectorAll("a[data-tab]")) {
        link.addEventListener("click", (e) => {
          // A new tab or window with a modifier key, as links do
          if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
          e.preventDefault();
          this._openTab(link.dataset.tab);
        });
      }
      root.querySelector("#back")?.addEventListener("click", () => this._close());
      root.getElementById("refresh").addEventListener("click", () => this._refresh());
      root.getElementById("integration").addEventListener("click", () => this._openIntegration());
      this._renderHeader();
      this._renderContent(root.getElementById("content"));
    }

    _renderContent(content) {
      if (!this._form) {
        if (this._tab === "rooms") this._renderRooms(content);
        else this._renderGuests(content);
      } else if (this._form.kind === "settings") this._renderSettingsForm(content);
      else this._renderGuestForm(content);
    }

    _errorAlert() {
      return this._error
        ? `<ha-alert alert-type="error">${esc(this._t("error", { message: this._error }))}</ha-alert>`
        : "";
    }

    _confirmAlert(action) {
      const c = this._confirm;
      if (!c || c.action !== action) return "";
      return `<ha-alert alert-type="warning">${esc(this._t(`${action}Confirm`, { name: c.name }))}
        <ha-button slot="action" appearance="plain" id="confirm-cancel">${esc(this._t("cancel"))}</ha-button>
        <ha-button slot="action" variant="danger" id="confirm-ok">${esc(this._t(action))}</ha-button>
      </ha-alert>`;
    }

    _bindConfirm(host) {
      host.querySelector("#confirm-cancel")?.addEventListener("click", () => {
        this._confirm = null;
        this._render();
      });
      host.querySelector("#confirm-ok")?.addEventListener("click", () => this._runConfirm());
    }

    // Tabs: the guests, and the residents with the lockable rooms

    _about() {
      const about = this._data?.about;
      return `<div class="about">${esc(
        // A release has no commit of its own; only a test deployment writes one
        this._t(about?.commit ? "aboutCommit" : "about", {
          version: about?.version ?? "",
          commit: about?.commit ?? "",
        }),
      )}</div>`;
    }

    _renderGuests(content) {
      const data = this._data;
      if (!data) {
        content.innerHTML = this._errorAlert();
        return;
      }
      const guests = data.guests
        .map((guest) => {
          const [icon, color] = STATUS[guest.state.status] ?? STATUS.away;
          const visit =
            guest.visit_minutes === null ? this._t("unlimited") : this._t("minutes", { n: guest.visit_minutes });
          const guestRooms = guest.all_rooms ? this._t("allRooms") : this._rooms(guest.rooms);
          return `
            <div class="item" data-edit="${esc(guest.id)}" role="button" tabindex="0">
              ${
                guest.picture
                  ? `<img class="icon photo" alt="" src="${esc(pictureUrl(guest.picture))}">`
                  : `<div class="icon" style="color:${color};background:color-mix(in srgb, ${color} 15%, transparent)">
                <ha-icon icon="${icon}"></ha-icon></div>`
              }
              <div class="text">
                <div class="headline">${esc(guest.name)} · ${esc(this._statusText(guest))}</div>
                <div class="supporting">${esc(this._approvalText(guest))}</div>
                <div class="supporting">${esc(guestRooms)} · ${esc(visit)}</div>
              </div>
              ${
                guest.approval.kind === "off"
                  ? ""
                  : `<ha-icon-button data-lock="${esc(guest.id)}" label="${esc(this._t("lock"))}"><ha-icon icon="mdi:lock-outline"></ha-icon></ha-icon-button>`
              }
              <ha-icon class="chevron" icon="mdi:chevron-right"></ha-icon>
            </div>`;
        })
        .join("");
      content.innerHTML = `
        ${this._errorAlert()}
        ${this._confirmAlert("lock")}
        <ha-card header="${esc(this._t("guests"))}">
          <div class="card-content list">
            ${guests || `<div class="empty">${esc(this._t("noGuests"))}</div>`}
          </div>
          <div class="card-actions">
            <ha-button id="add">${esc(this._t("addGuest"))}</ha-button>
          </div>
        </ha-card>
        ${this._about()}`;
      content.querySelector("#add").addEventListener("click", () => this._openGuest(null));
      for (const item of content.querySelectorAll("[data-edit]")) {
        item.addEventListener("click", () => this._openGuest(item.dataset.edit));
        item.addEventListener("keydown", (e) => {
          // Only the row itself; the lock button inside handles its own keys
          if (e.target !== item || (e.key !== "Enter" && e.key !== " ")) return;
          e.preventDefault();
          this._openGuest(item.dataset.edit);
        });
      }
      for (const button of content.querySelectorAll("[data-lock]")) {
        button.addEventListener("click", (e) => {
          e.stopPropagation();
          const guest = data.guests.find((g) => g.id === button.dataset.lock);
          this._confirm = { action: "lock", id: guest.id, name: guest.name };
          this._render();
        });
      }
      this._bindConfirm(content);
    }

    _renderRooms(content) {
      const data = this._data;
      if (!data) {
        content.innerHTML = this._errorAlert();
        return;
      }
      const lock = data.lock.active
        ? `<ha-alert alert-type="info">${esc(
            this._t("lockActive", { locked: this._rooms(data.lock.locked_rooms), free: this._rooms(data.lock.free_rooms) }),
          )}</ha-alert>`
        : "";
      const residents = data.settings.residents.map((id) => this._entityName(id)).join(", ") || this._t("none");
      content.innerHTML = `
        ${this._errorAlert()}
        ${lock}
        <ha-card header="${esc(this._t("settings"))}">
          <div class="card-content list">
            <div class="row"><div class="label">${esc(this._t("residents"))}</div>
              <div class="value">${esc(residents)}</div></div>
            <div class="row"><div class="label">${esc(this._t("lockableRooms"))}</div>
              <div class="value">${esc(this._rooms(data.settings.rooms.map((r) => r.area_id)))}</div></div>
            ${data.lock.active ? "" : `<div class="row"><div class="value supporting">${esc(this._t("lockOff"))}</div></div>`}
          </div>
          <div class="card-actions">
            <ha-button appearance="plain" id="settings">${esc(this._t("edit"))}</ha-button>
          </div>
        </ha-card>
        ${this._about()}`;
      content.querySelector("#settings").addEventListener("click", () => this._openSettings());
    }

    async _runConfirm() {
      const c = this._confirm;
      this._confirm = null;
      try {
        if (c.action === "lock") {
          await this._call({ type: "guest_access/lock_guest", guest_id: c.id });
        } else if (c.action === "logDelete") {
          await this._call({ type: "guest_access/delete_visits", guest_id: c.id });
        } else {
          await this._call({ type: "guest_access/delete_guest", guest_id: c.id });
          this._dropUploads(this._form);
          this._form = null;
        }
      } catch {
        // Shown on the page
      }
      this._render();
    }

    _openGuest(id) {
      const guest = this._data.guests.find((g) => g.id === id);
      const a = guest?.approval;
      this._form = {
        kind: "guest",
        id,
        originalName: guest?.name ?? "",
        main: {
          name: guest?.name ?? "",
          trackers: guest ? [...guest.trackers] : [],
        },
        approval: {
          kind: a?.kind ?? "once",
          until: localValue(a?.until),
          grace: guest?.grace_minutes ?? 15,
        },
        windows: (a?.windows ?? []).map((w) => ({
          weekdays: w.weekdays.map(String),
          start: withSeconds(w.start),
          end: withSeconds(w.end),
        })),
        rooms: {
          all_rooms: guest?.all_rooms ?? false,
          rooms: guest ? [...guest.rooms] : [],
          unlimited: guest ? guest.visit_minutes === null : false,
          visit_minutes: guest?.visit_minutes ?? 60,
        },
        log: { log_visits: guest?.log_visits ?? false },
        wasLogging: guest?.log_visits ?? false,
        media: { picture: guest?.picture ?? null, note: guest?.note ?? "" },
        // The photo is sent only when it changed here, so a form opened before
        // another change neither undoes that change nor sends a photo long gone
        originalPicture: guest?.picture ?? null,
        // Images uploaded while the form is open; the ones not saved are deleted
        uploaded: [],
      };
      this._error = "";
      this._confirm = null;
      this._render();
    }

    _openSettings() {
      this._form = {
        kind: "settings",
        main: { residents: [...this._data.settings.residents] },
        rooms: this._data.settings.rooms.map((room) => ({ ...room })),
        timings: {
          resume_minutes: this._data.settings.resume_minutes,
          log_grid_minutes: this._data.settings.log_grid_minutes,
          log_keep_days: this._data.settings.log_keep_days,
          log_keep_months: this._data.settings.log_keep_months,
        },
      };
      this._error = "";
      this._confirm = null;
      this._render();
    }

    // Delete the photos a form uploaded but did not save; Guest Access also deletes
    // them itself after an hour, this only does it at once
    _dropUploads(f) {
      if (!f?.uploaded?.length) return;
      // The photo of a save that is under way or done stays, whatever the form shows now
      const kept = f.saving || f.saved ? f.sentPicture : null;
      for (const id of f.uploaded) {
        if (id !== kept) this._call({ type: "image/delete", image_id: id }).catch(() => {});
      }
      f.uploaded = [];
    }

    _close() {
      this._dropUploads(this._form);
      this._form = null;
      this._error = "";
      this._confirm = null;
      this._render();
    }

    // ha-form with HA's own selectors; a change re-renders only when the schema changes

    _haForm(schema, data, onChange) {
      const form = document.createElement("ha-form");
      form.hass = this._hass;
      form.schema = schema;
      form.data = data;
      form.computeLabel = (s) => this._t(`field_${s.name}`);
      form.computeHelper = (s) => {
        const settings = this._data?.settings ?? {};
        const help = this._t(`help_${s.name}`, {
          grid: settings.log_grid_minutes,
          days: settings.log_keep_days,
          months: settings.log_keep_months,
        });
        return help === `help_${s.name}` ? undefined : help;
      };
      form.addEventListener("value-changed", (e) => {
        form.data = e.detail.value;
        onChange(e.detail.value);
      });
      return form;
    }

    _card(header, ...children) {
      const card = document.createElement("ha-card");
      if (header) card.header = header;
      const body = document.createElement("div");
      body.className = header ? "card-content" : "card-content top";
      body.append(...children);
      card.append(body);
      return card;
    }

    _note(text) {
      const p = document.createElement("p");
      p.className = "note";
      p.textContent = text;
      return p;
    }

    _iconButton(label, icon, onClick) {
      const button = document.createElement("ha-icon-button");
      button.label = label;
      button.innerHTML = `<ha-icon icon="${icon}"></ha-icon>`;
      button.addEventListener("click", onClick);
      return button;
    }

    _button(label, onClick, appearance = "plain") {
      const button = document.createElement("ha-button");
      if (appearance) button.setAttribute("appearance", appearance);
      button.textContent = label;
      button.addEventListener("click", onClick);
      return button;
    }

    _actions(save, withDelete) {
      const card = document.createElement("ha-card");
      const actions = document.createElement("div");
      actions.className = "card-actions";
      if (withDelete) {
        const del = this._button(this._t("delete"), () => {
          this._confirm = { action: "delete", id: this._form.id, name: this._form.originalName };
          this._render();
        });
        del.setAttribute("variant", "danger");
        actions.append(del);
      }
      const spacer = document.createElement("div");
      spacer.className = "spacer";
      actions.append(
        spacer,
        this._button(this._t("cancel"), () => this._close()),
        this._button(this._t("save"), save, null),
      );
      card.append(actions);
      return card;
    }

    _prepend(content, html) {
      if (!html) return;
      const holder = document.createElement("div");
      holder.innerHTML = html;
      content.append(...holder.childNodes);
    }

    // Guest form

    _renderGuestForm(content) {
      const f = this._form;
      const configured = this._data.settings.rooms.map((r) => r.area_id);
      content.innerHTML = "";
      this._prepend(content, this._errorAlert() + this._confirmAlert("delete") + this._confirmAlert("logDelete"));
      this._bindConfirm(content);

      content.append(
        this._card(
          "",
          this._haForm(
            [
              { name: "name", required: true, selector: { text: {} } },
              { name: "trackers", required: true, selector: { entity: { multiple: true, filter: { domain: "device_tracker" } } } },
            ],
            f.main,
            (value) => (f.main = value),
          ),
        ),
      );

      content.append(this._mediaCard(f));

      const withEnd = f.approval.kind === "once" || f.approval.kind === "until";
      const approvalSchema = [
        {
          name: "kind",
          required: true,
          selector: { select: { mode: "dropdown", options: KINDS.map((k) => ({ value: k, label: this._t(`kind_${k}`) })) } },
        },
      ];
      if (withEnd) approvalSchema.push({ name: "until", required: true, selector: { datetime: {} } });
      if (f.approval.kind !== "off") {
        approvalSchema.push({
          name: "grace",
          required: true,
          selector: { number: { min: 1, max: 240, mode: "box", unit_of_measurement: "min" } },
        });
      }
      content.append(
        this._card(
          this._t("approvalSection"),
          this._haForm(approvalSchema, f.approval, (value) => {
            const kindChanged = value.kind !== f.approval.kind;
            f.approval = value;
            if (kindChanged) this._render();
          }),
        ),
      );

      if (f.approval.kind === "until" || f.approval.kind === "permanent") {
        const entries = f.windows.map((w, n) => {
          const entry = document.createElement("div");
          entry.className = "entry";
          entry.append(
            this._haForm(
              [
                {
                  name: "weekdays",
                  required: true,
                  selector: {
                    select: {
                      multiple: true,
                      mode: "dropdown",
                      options: this._t("weekdays").map((d, i) => ({ value: String(i), label: d })),
                    },
                  },
                },
                {
                  type: "grid",
                  name: "",
                  schema: [
                    { name: "start", required: true, selector: { time: { no_second: true } } },
                    { name: "end", required: true, selector: { time: { no_second: true } } },
                  ],
                },
              ],
              w,
              (value) => (f.windows[n] = value),
            ),
            this._iconButton(this._t("removeWindow"), "mdi:delete-outline", () => {
              f.windows.splice(n, 1);
              this._render();
            }),
          );
          return entry;
        });
        const add = this._button(this._t("addWindow"), () => {
          f.windows.push({ weekdays: ["0", "1", "2", "3", "4"], start: "08:00:00", end: "18:00:00" });
          this._render();
        });
        content.append(this._card(this._t("windows"), this._note(this._t("windowsHelp")), ...entries, add));
      }

      const roomsSchema = [];
      if (configured.length) {
        roomsSchema.push({ name: "all_rooms", selector: { boolean: {} } });
        if (!f.rooms.all_rooms) {
          roomsSchema.push({
            name: "rooms",
            selector: {
              select: { multiple: true, mode: "list", options: configured.map((a) => ({ value: a, label: this._areaName(a) })) },
            },
          });
        }
      }
      roomsSchema.push({ name: "unlimited", selector: { boolean: {} } });
      if (!f.rooms.unlimited) {
        roomsSchema.push({
          name: "visit_minutes",
          required: true,
          selector: { number: { min: 1, max: 1440, mode: "box", unit_of_measurement: "min" } },
        });
      }
      const roomChildren = configured.length ? [] : [this._note(this._t("noRooms"))];
      content.append(
        this._card(
          this._t("roomsSection"),
          ...roomChildren,
          this._haForm(roomsSchema, f.rooms, (value) => {
            const changed = value.all_rooms !== f.rooms.all_rooms || value.unlimited !== f.rooms.unlimited;
            f.rooms = value;
            if (changed) this._render();
          }),
        ),
      );

      content.append(this._logCard(f));
      content.append(this._actions(() => this._saveGuest(), !!f.id));
    }

    // Visit log: date, start and length on the grid of the settings; no rooms, no places

    _hours(minutes) {
      return (minutes / 60).toLocaleString(this._hass.locale?.language || undefined, {
        maximumFractionDigits: 2,
      });
    }

    _logCard(f) {
      const children = [];
      const form = this._haForm(
        [{ name: "log_visits", selector: { boolean: {} } }],
        f.log,
        (value) => {
          const changed = value.log_visits !== f.log.log_visits;
          f.log = value;
          if (changed) this._render();
        },
      );
      children.push(form);
      const guest = f.id ? this._data.guests.find((g) => g.id === f.id) : null;
      if (guest && f.wasLogging && !f.log.log_visits && guest.log.visits.length) {
        const warn = document.createElement("ha-alert");
        warn.setAttribute("alert-type", "warning");
        warn.textContent = this._t("logOffNote");
        children.push(warn);
      }
      if (guest && f.log.log_visits && f.wasLogging) {
        const log = guest.log;
        const lang = this._hass.locale?.language || undefined;
        const lines = [];
        if (guest.state.counting && guest.state.arrived) {
          const since = new Date(guest.state.arrived);
          // On the grid of the log, as the finished visit will be
          const grid = (this._data.settings.log_grid_minutes || 15) * 60000;
          since.setTime(Math.round(since.getTime() / grid) * grid);
          lines.push(this._t("logRunning", { time: since.toLocaleString(lang, { dateStyle: "short", timeStyle: "short" }) }));
        }
        const [year, month] = log.this_month.split("-").map(Number);
        const last = month === 1 ? `${year - 1}-12` : `${year}-${String(month - 1).padStart(2, "0")}`;
        for (const [key, text] of [[log.this_month, "logMonth"], [last, "logLastMonth"]]) {
          const total = log.months[key] ?? { visits: 0, minutes: 0 };
          const visits = total.visits === 1 ? this._t("visitOne") : this._t("visitMany", { count: total.visits });
          lines.push(this._t(text, { visits, hours: this._hours(total.minutes) }));
        }
        for (const line of lines) children.push(this._note(line));
        const list = document.createElement("div");
        list.className = "visits";
        if (!log.visits.length) list.append(this._note(this._t("logNone")));
        for (const visit of log.visits.slice(0, 10)) {
          const start = new Date(visit.start);
          const end = new Date(start.getTime() + visit.minutes * 60000);
          const row = document.createElement("div");
          row.className = "visit";
          const when = document.createElement("span");
          when.textContent = `${start.toLocaleDateString(lang, { weekday: "short", day: "numeric", month: "numeric" })}, ${start.toLocaleTimeString(lang, { timeStyle: "short" })}–${end.toLocaleTimeString(lang, { timeStyle: "short" })}`;
          const length = document.createElement("span");
          length.textContent = `${this._hours(visit.minutes)} h`;
          row.append(when, length);
          list.append(row);
        }
        children.push(list);
        const actions = document.createElement("div");
        actions.className = "log-actions";
        const exportButton = this._button(this._t("logExport"), () => this._exportCsv(guest));
        exportButton.disabled = !log.visits.length;
        const deleteButton = this._button(this._t("logDelete"), () => {
          this._confirm = { action: "logDelete", id: guest.id, name: guest.name };
          this._render();
        });
        deleteButton.setAttribute("variant", "danger");
        deleteButton.disabled = !log.visits.length && !Object.keys(log.months).length;
        actions.append(exportButton, deleteButton);
        children.push(actions);
      }
      return this._card(this._t("logSection"), ...children);
    }

    _mediaCard(f) {
      const row = document.createElement("div");
      row.className = "media";
      let avatar;
      if (f.media.picture) {
        avatar = document.createElement("img");
        avatar.src = pictureUrl(f.media.picture);
        avatar.alt = "";
      } else {
        avatar = document.createElement("div");
        avatar.innerHTML = `<ha-icon icon="mdi:account"></ha-icon>`;
      }
      avatar.className = "avatar";
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "image/png,image/jpeg,image/gif";
      input.hidden = true;
      input.addEventListener("change", async () => {
        const file = input.files?.[0];
        if (!file) return;
        try {
          const id = await this._upload(file);
          f.uploaded.push(id);
          if (this._form !== f) {
            // The form was closed while the photo was uploading
            this._dropUploads(f);
            return;
          }
          f.media.picture = id;
          this._error = "";
        } catch (err) {
          this._error = err?.message || String(err);
        }
        this._render();
      });
      const actions = document.createElement("div");
      actions.className = "media-actions";
      actions.append(input, this._button(this._t("choosePhoto"), () => input.click()));
      if (f.media.picture) {
        actions.append(
          this._button(this._t("removePhoto"), () => {
            f.media.picture = null;
            this._render();
          }),
        );
      }
      actions.append(this._note(this._t("photoHelp")));
      row.append(avatar, actions);
      return this._card(
        this._t("mediaSection"),
        row,
        this._haForm(
          [{ name: "note", selector: { text: { multiline: true } } }],
          { note: f.media.note },
          (value) => (f.media.note = value.note ?? ""),
        ),
      );
    }

    // Upload a photo through Guest Access, into Home Assistant's images; its ID
    async _upload(file) {
      const form = new FormData();
      form.append("file", file);
      const response = await this._hass.fetchWithAuth("/api/guest_access/picture", { method: "POST", body: form });
      if (!response.ok) {
        const body = await response.text();
        let message = body;
        try {
          message = JSON.parse(body).message || body;
        } catch {
          // Not JSON: the text as it is
        }
        throw new Error(message);
      }
      return (await response.json()).id;
    }

    _exportCsv(guest) {
      const lang = this._hass.locale?.language || undefined;
      const rows = [this._t("csvHeader")];
      for (const visit of [...guest.log.visits].reverse()) {
        const start = new Date(visit.start);
        const end = new Date(start.getTime() + visit.minutes * 60000);
        const time = (d) => d.toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" });
        rows.push(
          [start.toLocaleDateString(lang), time(start), time(end), this._hours(visit.minutes)].join(";"),
        );
      }
      const blob = new Blob([`\ufeff${rows.join("\r\n")}\r\n`], { type: "text/csv;charset=utf-8" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      const safe = guest.name.replace(/[^\p{L}\p{N}_-]+/gu, "-");
      link.download = `guest-access-${safe}-${new Date().toISOString().slice(0, 10)}.csv`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    }

    async _saveGuest() {
      const f = this._form;
      if (f.saving) return;
      const kind = f.approval.kind;
      const withEnd = kind === "once" || kind === "until";
      const withWindow = kind === "until" || kind === "permanent";
      const until = withEnd && f.approval.until ? new Date(f.approval.until.replace(" ", "T")) : null;
      const message = {
        type: "guest_access/save_guest",
        name: (f.main.name || "").trim(),
        trackers: f.main.trackers || [],
        approval: {
          kind,
          until: until && !isNaN(until) ? until.toISOString() : null,
          windows: withWindow
            ? f.windows.map((w) => ({
                weekdays: (w.weekdays || []).map(Number).sort(),
                start: withoutSeconds(w.start),
                end: withoutSeconds(w.end),
              }))
            : [],
        },
        rooms: f.rooms.all_rooms ? [] : f.rooms.rooms || [],
        all_rooms: !!f.rooms.all_rooms,
        visit_minutes: f.rooms.unlimited ? null : Number(f.rooms.visit_minutes) || 60,
        grace_minutes: Number(f.approval.grace) || 15,
        log_visits: !!f.log.log_visits,
        note: (f.media.note || "").trim(),
      };
      if (f.media.picture !== f.originalPicture) message.picture = f.media.picture;
      if (f.id) message.guest_id = f.id;
      f.saving = true;
      f.sentPicture = f.media.picture;
      try {
        await this._call(message);
        f.saved = true;
      } catch {
        // Shown on the page
      }
      f.saving = false;
      if (!f.saved) return;
      // Another form may be open by now: close only the one that was saved
      if (this._form === f) this._close();
      else this._dropUploads(f);
    }

    // Settings form

    _renderSettingsForm(content) {
      const f = this._form;
      content.innerHTML = "";
      this._prepend(content, this._errorAlert());

      content.append(
        this._card(
          "",
          this._haForm(
            [{ name: "residents", selector: { entity: { multiple: true, filter: { domain: "person" } } } }],
            f.main,
            (value) => (f.main = value),
          ),
        ),
      );

      const entries = f.rooms.map((room, i) => {
        const entry = document.createElement("div");
        entry.className = "entry";
        entry.append(
          this._haForm(
            [
              {
                type: "grid",
                name: "",
                schema: [
                  { name: "area", required: true, selector: { area: {} } },
                  { name: "door", required: true, selector: { entity: { filter: { domain: "binary_sensor" } } } },
                ],
              },
            ],
            { area: room.area_id, door: room.door },
            (value) => (f.rooms[i] = { area_id: value.area || "", door: value.door || "" }),
          ),
          this._iconButton(this._t("removeRoom"), "mdi:delete-outline", () => {
            f.rooms.splice(i, 1);
            this._render();
          }),
        );
        return entry;
      });
      const add = this._button(this._t("addRoom"), () => {
        f.rooms.push({ area_id: "", door: "" });
        this._render();
      });
      content.append(this._card(this._t("lockableRooms"), this._note(this._t("roomsHelp")), ...entries, add));

      const minutes = (max) => ({ number: { min: 1, max, mode: "box", unit_of_measurement: "min" } });
      content.append(
        this._card(
          this._t("timingsSection"),
          this._haForm(
            [
              { name: "resume_minutes", required: true, selector: minutes(60) },
              { name: "log_grid_minutes", required: true, selector: minutes(60) },
              {
                type: "grid",
                name: "",
                schema: [
                  {
                    name: "log_keep_days",
                    required: true,
                    selector: { number: { min: 1, max: 3650, mode: "box", unit_of_measurement: "d" } },
                  },
                  {
                    name: "log_keep_months",
                    required: true,
                    selector: { number: { min: 1, max: 120, mode: "box" } },
                  },
                ],
              },
            ],
            f.timings,
            (value) => (f.timings = value),
          ),
        ),
      );

      content.append(
        this._actions(async () => {
          try {
            await this._call({
              type: "guest_access/save_settings",
              residents: f.main.residents || [],
              rooms: f.rooms.filter((r) => r.area_id || r.door),
              resume_minutes: Number(f.timings.resume_minutes),
              log_grid_minutes: Number(f.timings.log_grid_minutes),
              log_keep_days: Number(f.timings.log_keep_days),
              log_keep_months: Number(f.timings.log_keep_months),
            });
            this._close();
          } catch {
            // Shown on the page
          }
        }, false),
      );
    }
  }

  customElements.define("guest-access-panel", GuestAccessPanel);
}

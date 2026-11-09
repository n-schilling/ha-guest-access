// Guest Access panel: the page in the sidebar where administrators add guests,
// approve and lock them, and set the residents and the lockable rooms. Every
// change goes to the integration over the WebSocket API; the list follows the
// integration's state live.
//
// The page is built from Home Assistant's own elements (top app bar, cards,
// buttons, alerts and ha-form with selectors), so it looks and behaves like the
// rest of the UI. An edit opens as a subpage with a back arrow.

if (!customElements.get("guest-access-panel")) {
  const TEXTS = {
    en: {
      title: "Guest Access",
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
      logOffNote: "Saving deletes the visit log kept so far.",
      logRunning: "Visit running since {time}",
      logMonth: "This month: {visits} visits, {hours} h",
      logLastMonth: "Last month: {visits} visits, {hours} h",
      logNone: "No finished visits yet.",
      logExport: "Export as CSV",
      logDelete: "Delete log",
      logDeleteConfirm: "Delete the visit log of {name}?",
      csvHeader: "Date;Start;End;Hours",
      about: "Guest Access {version} · commit {commit}",
      unknownCommit: "unknown",
    },
    de: {
      title: "Guest Access",
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
      logOffNote: "Beim Speichern wird das bisherige Besuchsprotokoll gelöscht.",
      logRunning: "Besuch läuft seit {time}",
      logMonth: "Dieser Monat: {visits} Besuche, {hours} h",
      logLastMonth: "Letzter Monat: {visits} Besuche, {hours} h",
      logNone: "Noch keine abgeschlossenen Besuche.",
      logExport: "Als CSV exportieren",
      logDelete: "Protokoll löschen",
      logDeleteConfirm: "Besuchsprotokoll von {name} löschen?",
      csvHeader: "Datum;Beginn;Ende;Stunden",
      about: "Guest Access {version} · Commit {commit}",
      unknownCommit: "unbekannt",
    },
  };
  const KINDS = ["off", "once", "until", "permanent"];
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

  const STYLE = `
    :host { display: block; height: 100vh; height: 100dvh; background: var(--primary-background-color);
      color: var(--primary-text-color); }
    /* Like the settings and other panels: the header in the sidebar's colour, with a line */
    ha-top-app-bar-fixed { height: 100%;
      --app-header-background-color: var(--sidebar-background-color, var(--card-background-color));
      --app-header-border-bottom: 1px solid var(--divider-color); }
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
    }

    set hass(hass) {
      const first = !this._hass;
      this._hass = hass;
      if (first) {
        this._render();
        this._subscribe();
      }
      for (const el of this.shadowRoot.querySelectorAll("ha-menu-button, ha-form")) el.hass = hass;
    }

    set narrow(narrow) {
      this._narrow = narrow;
      const menu = this.shadowRoot.querySelector("ha-menu-button");
      if (menu) menu.narrow = narrow;
    }

    disconnectedCallback() {
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
          // An open form keeps what is being typed; only the list follows the state
          if (!this._form) this._render();
        },
        { type: "guest_access/subscribe" },
      );
      this._unsub.catch((err) => {
        this._error = err.message || String(err);
        this._render();
      });
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
      if (a.kind !== "off" && !guest.state.approval_valid) text += ` (${this._t("expired")})`;
      return text;
    }

    // The status comes from the integration, as on the guest's status sensor
    _statusText(guest) {
      const s = guest.state;
      let text = this._t(`status_${s.status}`);
      if (s.counting && s.visit_ends) text += ` ${this._t("visitEnds", { time: this._time(s.visit_ends) })}`;
      return text;
    }

    // Layout: the top app bar with the list, or a subpage with the form

    // The frame changes only between the list and a form, so a re-render of the
    // content keeps the scroll position
    _render() {
      const root = this.shadowRoot;
      const editing = !!this._form;
      const mode = editing ? `${this._form.kind}:${this._form.id ?? ""}` : "list";
      if (this._mode === mode && root.getElementById("content")) {
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
      root.innerHTML = `
        <style>${STYLE}</style>
        <ha-top-app-bar-fixed>
          ${
            editing
              ? `<ha-icon-button slot="navigationIcon" id="back" label="${esc(this._t("back"))}"><ha-icon icon="mdi:arrow-left"></ha-icon></ha-icon-button>`
              : `<ha-menu-button slot="navigationIcon"></ha-menu-button>`
          }
          <div slot="title">${esc(title)}</div>
          <div class="content" id="content"></div>
        </ha-top-app-bar-fixed>`;
      const menu = root.querySelector("ha-menu-button");
      if (menu) {
        menu.hass = this._hass;
        menu.narrow = this._narrow;
      }
      root.querySelector("#back")?.addEventListener("click", () => this._close());
      this._renderContent(root.getElementById("content"));
    }

    _renderContent(content) {
      if (!this._form) this._renderList(content);
      else if (this._form.kind === "settings") this._renderSettingsForm(content);
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

    // List

    _renderList(content) {
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
      const guests = data.guests
        .map((guest) => {
          const [icon, color] = STATUS[guest.state.status] ?? STATUS.away;
          const visit =
            guest.visit_minutes === null ? this._t("unlimited") : this._t("minutes", { n: guest.visit_minutes });
          const guestRooms = guest.all_rooms ? this._t("allRooms") : this._rooms(guest.rooms);
          return `
            <div class="item" data-edit="${esc(guest.id)}" role="button" tabindex="0">
              <div class="icon" style="color:${color};background:color-mix(in srgb, ${color} 15%, transparent)">
                <ha-icon icon="${icon}"></ha-icon></div>
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
      const residents = data.settings.residents.map((id) => this._entityName(id)).join(", ") || this._t("none");
      content.innerHTML = `
        ${this._errorAlert()}
        ${this._confirmAlert("lock")}
        ${lock}
        <ha-card header="${esc(this._t("guests"))}">
          <div class="card-content list">
            ${guests || `<div class="empty">${esc(this._t("noGuests"))}</div>`}
          </div>
          <div class="card-actions">
            <ha-button id="add">${esc(this._t("addGuest"))}</ha-button>
          </div>
        </ha-card>
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
        <div class="about">${esc(
          this._t("about", {
            version: data.about?.version ?? "",
            commit: data.about?.commit ?? this._t("unknownCommit"),
          }),
        )}</div>`;
      content.querySelector("#add").addEventListener("click", () => this._openGuest(null));
      content.querySelector("#settings").addEventListener("click", () => this._openSettings());
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

    _close() {
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
          lines.push(this._t(text, { visits: total.visits, hours: this._hours(total.minutes) }));
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
          when.textContent = `${start.toLocaleDateString(lang, { weekday: "short", day: "numeric", month: "numeric" })}, ${start.toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" })}–${end.toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" })}`;
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
      };
      if (f.id) message.guest_id = f.id;
      try {
        await this._call(message);
        this._close();
      } catch {
        // Shown on the page
      }
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

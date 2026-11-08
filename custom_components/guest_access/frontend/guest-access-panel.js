// Guest Access panel: the page in the sidebar where administrators add guests,
// approve and lock them, and set the residents and the lockable rooms. Every
// change goes to the integration over the WebSocket API; the list follows the
// integration's state live.

if (!customElements.get("guest-access-panel")) {
  const TEXTS = {
    en: {
      title: "Guest Access",
      guests: "Guests",
      addGuest: "Add guest",
      noGuests: "No guests yet.",
      settings: "Residents and rooms",
      edit: "Edit",
      lock: "Lock",
      lockConfirm: "Lock {name}? The guest no longer counts.",
      delete: "Delete",
      deleteConfirm: "Delete {name} with the device and its entities?",
      save: "Save",
      cancel: "Cancel",
      name: "Name",
      trackers: "Trackers",
      addTracker: "Add tracker",
      approval: "Approval",
      kind_off: "Locked",
      kind_once: "Once until",
      kind_until: "Permanent until",
      kind_permanent: "Permanent",
      until: "Until",
      expired: "expired",
      useWindow: "Only in a time window",
      from: "From",
      to: "To",
      grace: "Grace time (min) after leaving",
      rooms: "Rooms on top of the living area",
      allRooms: "All rooms",
      noRooms: "No lockable rooms set yet.",
      visit: "Time per visit",
      unlimited: "unlimited",
      minutes: "{n} min",
      counts: "Counts",
      countsUntil: "Counts, visit ends {time}",
      timeUp: "time is up",
      homeNotCounting: "Home, does not count",
      resuming: "Waiting after a restart",
      away: "Away",
      residents: "Residents",
      lockableRooms: "Lockable rooms",
      area: "Area",
      door: "Door contact",
      addRoom: "Add room",
      remove: "Remove",
      lockActive: "Room lock active. Locked: {locked}. Free: {free}.",
      lockOff: "Room lock off: a resident is home or no guest counts.",
      none: "none",
      error: "Error: {message}",
      weekdays: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
    },
    de: {
      title: "Guest Access",
      guests: "Gäste",
      addGuest: "Gast hinzufügen",
      noGuests: "Noch keine Gäste.",
      settings: "Bewohner und Räume",
      edit: "Bearbeiten",
      lock: "Sperren",
      lockConfirm: "{name} sperren? Der Gast zählt dann nicht mehr.",
      delete: "Löschen",
      deleteConfirm: "{name} mit Gerät und Entitäten löschen?",
      save: "Speichern",
      cancel: "Abbrechen",
      name: "Name",
      trackers: "Tracker",
      addTracker: "Tracker hinzufügen",
      approval: "Freigabe",
      kind_off: "Gesperrt",
      kind_once: "Einmalig bis",
      kind_until: "Dauerhaft bis",
      kind_permanent: "Dauerhaft",
      until: "Bis",
      expired: "abgelaufen",
      useWindow: "Nur in einem Zeitfenster",
      from: "Von",
      to: "Bis",
      grace: "Kulanzzeit (min) nach dem Gehen",
      rooms: "Räume zusätzlich zum Wohnbereich",
      allRooms: "Alle Räume",
      noRooms: "Noch keine sperrbaren Räume festgelegt.",
      visit: "Dauer je Besuch",
      unlimited: "unbegrenzt",
      minutes: "{n} min",
      counts: "Zählt",
      countsUntil: "Zählt, Besuch endet {time}",
      timeUp: "Zeit ist um",
      homeNotCounting: "Daheim, zählt nicht",
      resuming: "Wartet nach Neustart",
      away: "Weg",
      residents: "Bewohner",
      lockableRooms: "Sperrbare Räume",
      area: "Bereich",
      door: "Türkontakt",
      addRoom: "Raum hinzufügen",
      remove: "Entfernen",
      lockActive: "Raumsperre aktiv. Gesperrt: {locked}. Frei: {free}.",
      lockOff: "Raumsperre aus: ein Bewohner ist daheim oder kein Gast zählt.",
      none: "keine",
      error: "Fehler: {message}",
      weekdays: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
    },
  };
  const VISITS = [30, 60, 120, null];
  const KINDS = ["off", "once", "until", "permanent"];

  const esc = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
  const pad = (n) => String(n).padStart(2, "0");
  // A Date as the value of a datetime-local input, in local time
  const localInput = (iso) => {
    if (!iso) return "";
    const d = new Date(iso);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const STYLE = `
    :host { display: block; background: var(--primary-background-color); color: var(--primary-text-color);
      min-height: 100vh; min-height: 100dvh; font-family: var(--ha-font-family-body, Roboto, sans-serif); }
    header { display: flex; align-items: center; gap: 8px; height: 56px; padding: 0 12px;
      background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff);
      font-size: 20px; }
    main { max-width: 860px; margin: 0 auto; padding: 16px; box-sizing: border-box; }
    .card { background: var(--card-background-color); border-radius: var(--ha-card-border-radius, 12px);
      border: 1px solid var(--divider-color); padding: 16px; margin-bottom: 16px; }
    h2 { font-size: 18px; font-weight: 500; margin: 0 0 12px; display: flex; align-items: center; gap: 8px; }
    h2 .grow { flex: 1; }
    .guest { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; padding: 12px 0;
      border-top: 1px solid var(--divider-color); }
    .guest:first-of-type { border-top: none; }
    .guest .info { flex: 1; min-width: 200px; }
    .guest .name { font-weight: 500; }
    .muted { color: var(--secondary-text-color); font-size: 14px; }
    .state { font-size: 14px; }
    .on { color: var(--success-color, #43a047); }
    .warn { color: var(--warning-color, #ffa600); }
    button { font: inherit; font-size: 14px; border-radius: 8px; padding: 6px 14px; cursor: pointer;
      border: 1px solid var(--primary-color); background: transparent; color: var(--primary-color); }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    button.danger { border-color: var(--error-color, #db4437); color: var(--error-color, #db4437); }
    label { display: block; font-size: 14px; margin: 12px 0 4px; color: var(--secondary-text-color); }
    label.inline { display: inline-flex; align-items: center; gap: 6px; margin: 4px 12px 4px 0;
      color: var(--primary-text-color); }
    input, select { font: inherit; font-size: 15px; padding: 8px; border-radius: 8px; box-sizing: border-box;
      border: 1px solid var(--divider-color); background: var(--input-fill-color, var(--card-background-color));
      color: var(--primary-text-color); max-width: 100%; }
    input[type=checkbox] { padding: 0; }
    .row { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; flex-wrap: wrap; }
    .row input:not([type=checkbox]), .row select { flex: 1; min-width: 160px; }
    .actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; flex-wrap: wrap; }
    .error { color: var(--error-color, #db4437); margin-top: 12px; }
    [hidden] { display: none !important; }
  `;

  class GuestAccessPanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._data = null;
      // What is being edited: null, {kind: "guest", ...} or {kind: "settings", ...}
      this._form = null;
      this._error = "";
    }

    set hass(hass) {
      const first = !this._hass;
      this._hass = hass;
      if (first) {
        this._renderFrame();
        this._subscribe();
      }
      const menu = this.shadowRoot.querySelector("ha-menu-button");
      if (menu) menu.hass = hass;
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
        for (const [name, value] of Object.entries(values)) text = text.replace(`{${name}}`, value);
      }
      return text;
    }

    _subscribe() {
      this._unsub = this._hass.connection.subscribeMessage(
        (data) => {
          this._data = data;
          this._renderList();
        },
        { type: "guest_access/subscribe" },
      );
      this._unsub.catch((err) => {
        this._error = err.message || String(err);
        this._renderList();
      });
    }

    async _call(message) {
      this._error = "";
      try {
        return await this._hass.callWS(message);
      } catch (err) {
        this._error = err.message || String(err);
        this._renderForm();
        this._renderList();
        throw err;
      }
    }

    // Layout: the list follows the state, the form stays while it is edited

    _renderFrame() {
      this.shadowRoot.innerHTML = `
        <style>${STYLE}</style>
        <header><ha-menu-button></ha-menu-button><span>${esc(this._t("title"))}</span></header>
        <main><div id="form"></div><div id="list"></div></main>`;
      const menu = this.shadowRoot.querySelector("ha-menu-button");
      menu.hass = this._hass;
      menu.narrow = this._narrow;
    }

    _areaName(areaId) {
      return this._hass.areas?.[areaId]?.name || areaId;
    }

    _entityName(entityId) {
      return this._hass.states[entityId]?.attributes?.friendly_name || entityId;
    }

    _time(iso) {
      const d = new Date(iso);
      return d.toLocaleString(this._hass.locale?.language || undefined, {
        dateStyle: "short",
        timeStyle: "short",
      });
    }

    _approvalText(guest) {
      const a = guest.approval;
      let text = this._t(`kind_${a.kind}`);
      if (a.until) text += ` ${this._time(a.until)}`;
      if (a.window) {
        const days = a.window.weekdays.map((d) => this._t("weekdays")[d]).join(", ");
        text += ` · ${days} ${a.window.start}–${a.window.end}`;
      }
      if (a.kind !== "off" && !guest.state.approval_valid) text += ` (${this._t("expired")})`;
      return text;
    }

    _stateText(guest) {
      const s = guest.state;
      if (s.counting) {
        let text = s.visit_ends
          ? this._t("countsUntil", { time: this._time(s.visit_ends) })
          : this._t("counts");
        if (s.time_up) text += ` · ${this._t("timeUp")}`;
        return [text, s.time_up || s.approval_expired ? "warn" : "on"];
      }
      if (s.resume_until) return [this._t("resuming"), "muted"];
      if (s.home) return [this._t("homeNotCounting"), "warn"];
      return [this._t("away"), "muted"];
    }

    _renderList() {
      const list = this.shadowRoot.getElementById("list");
      if (!list) return;
      const data = this._data;
      if (!data) {
        list.innerHTML = this._error
          ? `<div class="card error">${esc(this._t("error", { message: this._error }))}</div>`
          : "";
        return;
      }
      const rooms = (ids) => ids.map((id) => esc(this._areaName(id))).join(", ") || this._t("none");
      const lock = data.lock.active
        ? this._t("lockActive", { locked: rooms(data.lock.locked_rooms), free: rooms(data.lock.free_rooms) })
        : this._t("lockOff");
      const guests = data.guests
        .map((guest) => {
          const [state, cls] = this._stateText(guest);
          const visit =
            guest.visit_minutes === null ? this._t("unlimited") : this._t("minutes", { n: guest.visit_minutes });
          const guestRooms = guest.all_rooms ? this._t("allRooms") : rooms(guest.rooms);
          return `
            <div class="guest">
              <div class="info">
                <div class="name">${esc(guest.name)}</div>
                <div class="state ${cls}">${esc(state)}</div>
                <div class="muted">${esc(this._approvalText(guest))}</div>
                <div class="muted">${guestRooms} · ${esc(visit)}</div>
              </div>
              <button data-edit="${esc(guest.id)}">${esc(this._t("edit"))}</button>
              <button class="danger" data-lock="${esc(guest.id)}" ${guest.approval.kind === "off" ? "hidden" : ""}>${esc(this._t("lock"))}</button>
            </div>`;
        })
        .join("");
      list.innerHTML = `
        <div class="card">
          <h2><span class="grow">${esc(this._t("guests"))}</span>
            <button class="primary" id="add">${esc(this._t("addGuest"))}</button></h2>
          ${guests || `<div class="muted">${esc(this._t("noGuests"))}</div>`}
        </div>
        <div class="card">
          <h2><span class="grow">${esc(this._t("settings"))}</span>
            <button id="settings">${esc(this._t("edit"))}</button></h2>
          <div class="muted">${esc(this._t("residents"))}: ${
            data.settings.residents.map((id) => esc(this._entityName(id))).join(", ") || this._t("none")
          }</div>
          <div class="muted">${esc(this._t("lockableRooms"))}: ${rooms(data.settings.rooms.map((r) => r.area_id))}</div>
          <div class="muted">${lock}</div>
        </div>`;
      list.querySelector("#add").addEventListener("click", () => this._openGuest(null));
      list.querySelector("#settings").addEventListener("click", () => this._openSettings());
      for (const button of list.querySelectorAll("[data-edit]")) {
        button.addEventListener("click", () => this._openGuest(button.dataset.edit));
      }
      for (const button of list.querySelectorAll("[data-lock]")) {
        button.addEventListener("click", () => this._lock(button.dataset.lock));
      }
    }

    // Guest form

    _openGuest(id) {
      const guest = this._data.guests.find((g) => g.id === id);
      const a = guest?.approval;
      this._form = {
        kind: "guest",
        id,
        name: guest?.name ?? "",
        trackers: guest ? [...guest.trackers] : [""],
        approval: a?.kind ?? "once",
        until: localInput(a?.until),
        useWindow: Boolean(a?.window),
        weekdays: a?.window?.weekdays ?? [0, 1, 2, 3, 4],
        start: a?.window?.start ?? "08:00",
        end: a?.window?.end ?? "18:00",
        grace: guest?.grace_minutes ?? 15,
        rooms: guest ? [...guest.rooms] : [],
        allRooms: guest?.all_rooms ?? false,
        visit: guest ? guest.visit_minutes : 60,
      };
      this._error = "";
      this._renderForm();
    }

    _openSettings() {
      this._form = {
        kind: "settings",
        residents: [...this._data.settings.residents],
        rooms: this._data.settings.rooms.map((room) => ({ ...room })),
      };
      this._error = "";
      this._renderForm();
    }

    _close() {
      this._form = null;
      this._error = "";
      this._renderForm();
    }

    _renderForm() {
      const host = this.shadowRoot.getElementById("form");
      if (!host) return;
      if (!this._form) {
        host.innerHTML = "";
        return;
      }
      if (this._form.kind === "settings") this._renderSettingsForm(host);
      else this._renderGuestForm(host);
    }

    _entities(domain) {
      return Object.keys(this._hass.states)
        .filter((id) => id.startsWith(`${domain}.`))
        .sort();
    }

    _datalist(id, domain) {
      return `<datalist id="${id}">${this._entities(domain)
        .map((e) => `<option value="${esc(e)}">${esc(this._entityName(e))}</option>`)
        .join("")}</datalist>`;
    }

    _renderGuestForm(host) {
      const f = this._form;
      const configured = this._data.settings.rooms.map((r) => r.area_id);
      const withEnd = f.approval === "once" || f.approval === "until";
      const withWindow = f.approval === "until" || f.approval === "permanent";
      host.innerHTML = `
        <div class="card">
          <h2>${esc(f.id ? f.name || this._t("edit") : this._t("addGuest"))}</h2>
          <label>${esc(this._t("name"))}</label>
          <input id="name" value="${esc(f.name)}" style="width:100%">
          <label>${esc(this._t("trackers"))}</label>
          ${f.trackers
            .map(
              (t, i) => `<div class="row">
                <input list="trackers" data-tracker="${i}" value="${esc(t)}" placeholder="device_tracker.…">
                <button data-remove-tracker="${i}">${esc(this._t("remove"))}</button></div>`,
            )
            .join("")}
          ${this._datalist("trackers", "device_tracker")}
          <button id="add-tracker">${esc(this._t("addTracker"))}</button>
          <label>${esc(this._t("approval"))}</label>
          <div class="row">
            <select id="approval">${KINDS.map(
              (k) => `<option value="${k}" ${k === f.approval ? "selected" : ""}>${esc(this._t(`kind_${k}`))}</option>`,
            ).join("")}</select>
            <input id="until" type="datetime-local" value="${esc(f.until)}" ${withEnd ? "" : "hidden"}>
          </div>
          <div ${withWindow ? "" : "hidden"}>
            <label class="inline"><input type="checkbox" id="use-window" ${f.useWindow ? "checked" : ""}>${esc(this._t("useWindow"))}</label>
            <div ${f.useWindow ? "" : "hidden"}>
              <div>${this._t("weekdays")
                .map(
                  (d, i) => `<label class="inline"><input type="checkbox" data-day="${i}" ${f.weekdays.includes(i) ? "checked" : ""}>${esc(d)}</label>`,
                )
                .join("")}</div>
              <div class="row">${esc(this._t("from"))} <input id="start" type="time" value="${esc(f.start)}">
                ${esc(this._t("to"))} <input id="end" type="time" value="${esc(f.end)}"></div>
            </div>
          </div>
          <div ${f.approval === "once" ? "" : "hidden"}>
            <label>${esc(this._t("grace"))}</label>
            <input id="grace" type="number" min="1" max="240" value="${esc(f.grace)}">
          </div>
          <label>${esc(this._t("rooms"))}</label>
          ${
            configured.length
              ? `<label class="inline"><input type="checkbox" id="all-rooms" ${f.allRooms ? "checked" : ""}>${esc(this._t("allRooms"))}</label>
                 ${configured
                   .map(
                     (a) => `<label class="inline"><input type="checkbox" data-room="${esc(a)}"
                       ${f.allRooms || f.rooms.includes(a) ? "checked" : ""} ${f.allRooms ? "disabled" : ""}>${esc(this._areaName(a))}</label>`,
                   )
                   .join("")}`
              : `<div class="muted">${esc(this._t("noRooms"))}</div>`
          }
          <label>${esc(this._t("visit"))}</label>
          <select id="visit">${VISITS.map(
            (v) => `<option value="${v ?? ""}" ${v === f.visit ? "selected" : ""}>${esc(
              v === null ? this._t("unlimited") : this._t("minutes", { n: v }),
            )}</option>`,
          ).join("")}</select>
          ${this._error ? `<div class="error">${esc(this._t("error", { message: this._error }))}</div>` : ""}
          <div class="actions">
            ${f.id ? `<button class="danger" id="delete">${esc(this._t("delete"))}</button>` : ""}
            <button id="cancel">${esc(this._t("cancel"))}</button>
            <button class="primary" id="save">${esc(this._t("save"))}</button>
          </div>
        </div>`;
      const $ = (sel) => host.querySelector(sel);
      $("#name").addEventListener("input", (e) => (f.name = e.target.value));
      for (const input of host.querySelectorAll("[data-tracker]")) {
        input.addEventListener("input", (e) => (f.trackers[Number(input.dataset.tracker)] = e.target.value));
      }
      for (const button of host.querySelectorAll("[data-remove-tracker]")) {
        button.addEventListener("click", () => {
          f.trackers.splice(Number(button.dataset.removeTracker), 1);
          this._renderForm();
        });
      }
      $("#add-tracker").addEventListener("click", () => {
        f.trackers.push("");
        this._renderForm();
      });
      $("#approval").addEventListener("change", (e) => {
        f.approval = e.target.value;
        this._renderForm();
      });
      $("#until").addEventListener("input", (e) => (f.until = e.target.value));
      $("#use-window").addEventListener("change", (e) => {
        f.useWindow = e.target.checked;
        this._renderForm();
      });
      for (const box of host.querySelectorAll("[data-day]")) {
        box.addEventListener("change", () => {
          const day = Number(box.dataset.day);
          f.weekdays = box.checked ? [...f.weekdays, day].sort() : f.weekdays.filter((d) => d !== day);
        });
      }
      $("#start").addEventListener("input", (e) => (f.start = e.target.value));
      $("#end").addEventListener("input", (e) => (f.end = e.target.value));
      $("#grace").addEventListener("input", (e) => (f.grace = Number(e.target.value)));
      $("#all-rooms")?.addEventListener("change", (e) => {
        f.allRooms = e.target.checked;
        this._renderForm();
      });
      for (const box of host.querySelectorAll("[data-room]")) {
        box.addEventListener("change", () => {
          const room = box.dataset.room;
          f.rooms = box.checked ? [...f.rooms, room] : f.rooms.filter((r) => r !== room);
        });
      }
      $("#visit").addEventListener("change", (e) => (f.visit = e.target.value === "" ? null : Number(e.target.value)));
      $("#cancel").addEventListener("click", () => this._close());
      $("#save").addEventListener("click", () => this._saveGuest());
      $("#delete")?.addEventListener("click", () => this._delete());
    }

    async _saveGuest() {
      const f = this._form;
      const withEnd = f.approval === "once" || f.approval === "until";
      const withWindow = (f.approval === "until" || f.approval === "permanent") && f.useWindow;
      const message = {
        type: "guest_access/save_guest",
        name: f.name,
        trackers: f.trackers.map((t) => t.trim()).filter(Boolean),
        approval: {
          kind: f.approval,
          until: withEnd && f.until ? new Date(f.until).toISOString() : null,
          window: withWindow ? { weekdays: f.weekdays, start: f.start, end: f.end } : null,
        },
        rooms: f.allRooms ? [] : f.rooms,
        all_rooms: f.allRooms,
        visit_minutes: f.visit,
        grace_minutes: f.grace,
      };
      if (f.id) message.guest_id = f.id;
      try {
        await this._call(message);
        this._close();
      } catch {
        // Shown in the form
      }
    }

    async _delete() {
      const f = this._form;
      if (!confirm(this._t("deleteConfirm", { name: f.name }))) return;
      try {
        await this._call({ type: "guest_access/delete_guest", guest_id: f.id });
        this._close();
      } catch {
        // Shown in the form
      }
    }

    async _lock(id) {
      const guest = this._data.guests.find((g) => g.id === id);
      if (!guest || !confirm(this._t("lockConfirm", { name: guest.name }))) return;
      try {
        await this._call({ type: "guest_access/lock_guest", guest_id: id });
      } catch {
        // Shown in the list
      }
    }

    // Settings form

    _renderSettingsForm(host) {
      const f = this._form;
      const areas = Object.values(this._hass.areas || {}).sort((a, b) => a.name.localeCompare(b.name));
      host.innerHTML = `
        <div class="card">
          <h2>${esc(this._t("settings"))}</h2>
          <label>${esc(this._t("residents"))}</label>
          <div>${this._entities("person")
            .map(
              (p) => `<label class="inline"><input type="checkbox" data-resident="${esc(p)}"
                ${f.residents.includes(p) ? "checked" : ""}>${esc(this._entityName(p))}</label>`,
            )
            .join("")}</div>
          <label>${esc(this._t("lockableRooms"))}</label>
          ${f.rooms
            .map(
              (room, i) => `<div class="row">
                <select data-area="${i}" aria-label="${esc(this._t("area"))}">
                  <option value=""></option>
                  ${areas
                    .map(
                      (a) => `<option value="${esc(a.area_id)}" ${a.area_id === room.area_id ? "selected" : ""}>${esc(a.name)}</option>`,
                    )
                    .join("")}
                </select>
                <input list="doors" data-door="${i}" value="${esc(room.door)}" placeholder="${esc(this._t("door"))}">
                <button data-remove-room="${i}">${esc(this._t("remove"))}</button></div>`,
            )
            .join("")}
          ${this._datalist("doors", "binary_sensor")}
          <button id="add-room">${esc(this._t("addRoom"))}</button>
          ${this._error ? `<div class="error">${esc(this._t("error", { message: this._error }))}</div>` : ""}
          <div class="actions">
            <button id="cancel">${esc(this._t("cancel"))}</button>
            <button class="primary" id="save">${esc(this._t("save"))}</button>
          </div>
        </div>`;
      for (const box of host.querySelectorAll("[data-resident]")) {
        box.addEventListener("change", () => {
          const id = box.dataset.resident;
          f.residents = box.checked ? [...f.residents, id] : f.residents.filter((r) => r !== id);
        });
      }
      for (const select of host.querySelectorAll("[data-area]")) {
        select.addEventListener("change", () => (f.rooms[Number(select.dataset.area)].area_id = select.value));
      }
      for (const input of host.querySelectorAll("[data-door]")) {
        input.addEventListener("input", () => (f.rooms[Number(input.dataset.door)].door = input.value.trim()));
      }
      for (const button of host.querySelectorAll("[data-remove-room]")) {
        button.addEventListener("click", () => {
          f.rooms.splice(Number(button.dataset.removeRoom), 1);
          this._renderForm();
        });
      }
      host.querySelector("#add-room").addEventListener("click", () => {
        f.rooms.push({ area_id: "", door: "" });
        this._renderForm();
      });
      host.querySelector("#cancel").addEventListener("click", () => this._close());
      host.querySelector("#save").addEventListener("click", async () => {
        try {
          await this._call({
            type: "guest_access/save_settings",
            residents: f.residents,
            rooms: f.rooms.filter((r) => r.area_id || r.door),
          });
          this._close();
        } catch {
          // Shown in the form
        }
      });
    }
  }

  customElements.define("guest-access-panel", GuestAccessPanel);
}

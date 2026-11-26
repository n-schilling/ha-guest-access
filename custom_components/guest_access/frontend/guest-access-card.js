// Guest Access card: a short overview of the guests for every user, or a welcome
// for the guests themselves. It only reads entities, changes nothing and uses
// none of the administrators' commands.
(() => {
  const DOMAIN = "guest_access";
  const TAG = "guest-access-card";
  // Statuses of a guest who is there and counts, or is about to again after a restart
  const PRESENT = ["counting", "time_up", "approval_expired", "resuming"];
  // The card from most to least: what does not fit is left out in this order
  const SIZES = ["large", "medium", "small"];

  const TEXTS = {
    en: {
      name: "Guest Access",
      description: "Who is visiting, until when and which rooms are locked; or a welcome for the guests.",
      title: "Guests",
      nobody: "Nobody visiting",
      onlyGuests: "Only guests home",
      guestsHome: "{count} guests home",
      guestHome: "1 guest home",
      andOne: "{name} and 1 more",
      andMore: "{name} and {count} more",
      until: "until {time}",
      timeUp: "time up",
      lockActive: "Room lock active",
      noLock: "No room lock",
      free: "{room} free",
      open: "{room} open",
      unreachableOne: "1 sensor unreachable",
      unreachableMany: "{count} sensors unreachable",
      unapprovedOne: "1 guest without approval",
      unapprovedMany: "{count} guests without approval",
      missing: "Guest Access is not set up.",
      welcome: "Welcome",
      welcomeNames: "Welcome, {names}",
      and: "and",
      greetingOne: "Good to have you here.",
      greetingMany: "Good to have you here.",
      yourVisit: "Your visit",
      visitUntil: "until {time}",
      minutesLeft: "{minutes} minutes left",
      minuteLeft: "1 minute left",
      hoursLeft: "{hours} h {minutes} min left",
      timeUpText: "Your visit time is up.",
      openForYou: "Open for you",
      keepClosed: "Please keep closed",
      otherRooms: "all other rooms",
      mode: "View",
      modeOverview: "Overview for residents",
      modeGuest: "Welcome for guests",
      size: "Size",
      sizeAuto: "By the space the card gets",
      sizeSmall: "Small",
      sizeMedium: "Medium",
      sizeLarge: "Large",
      sectionOverview: "Overview: what to show",
      sectionGuest: "Welcome: what to show",
      show_summary: "Overall state",
      show_guests: "Guests who count",
      show_visit_end: "End of the visit",
      show_status: "Status of each guest",
      show_rooms: "Room lock and rooms",
      show_unreachable: "Unreachable sensors",
      show_unapproved: "Number of guests without approval",
      show_visit: "End of the visit and time left",
      show_guest_rooms: "Rooms that are open and closed",
      greeting_text: "Line under the welcome",
      other_rooms_text: "Text for the rooms not named",
      time_up_text: "Text when the visit time is up",
      helpOtherRooms: "Shown with the rooms that are open; empty leaves it out.",
    },
    de: {
      name: "Guest Access",
      description: "Wer zu Besuch ist, bis wann und welche Räume gesperrt sind; oder eine Begrüßung für die Gäste.",
      title: "Gäste",
      nobody: "Niemand zu Besuch",
      onlyGuests: "Nur Gäste daheim",
      guestsHome: "{count} Gäste daheim",
      guestHome: "1 Gast daheim",
      andOne: "{name} und 1 weiterer",
      andMore: "{name} und {count} weitere",
      until: "bis {time}",
      timeUp: "Zeit um",
      lockActive: "Raumsperre aktiv",
      noLock: "Keine Raumsperre",
      free: "{room} frei",
      open: "{room} offen",
      unreachableOne: "1 Sensor nicht erreichbar",
      unreachableMany: "{count} Sensoren nicht erreichbar",
      unapprovedOne: "1 Gast ohne Freigabe",
      unapprovedMany: "{count} Gäste ohne Freigabe",
      missing: "Guest Access ist nicht eingerichtet.",
      welcome: "Willkommen",
      welcomeNames: "Willkommen, {names}",
      and: "und",
      greetingOne: "Schön, dass du da bist.",
      greetingMany: "Schön, dass ihr da seid.",
      yourVisit: "Dein Besuch",
      visitUntil: "bis {time} Uhr",
      minutesLeft: "noch {minutes} Minuten",
      minuteLeft: "noch 1 Minute",
      hoursLeft: "noch {hours} h {minutes} min",
      timeUpText: "Deine Besuchszeit ist um.",
      openForYou: "Für dich offen",
      keepClosed: "Bitte geschlossen lassen",
      otherRooms: "alle anderen Räume",
      mode: "Ansicht",
      modeOverview: "Übersicht für Bewohner",
      modeGuest: "Begrüßung für Gäste",
      size: "Größe",
      sizeAuto: "Nach dem Platz, den die Karte bekommt",
      sizeSmall: "Klein",
      sizeMedium: "Mittel",
      sizeLarge: "Groß",
      sectionOverview: "Übersicht: was gezeigt wird",
      sectionGuest: "Begrüßung: was gezeigt wird",
      show_summary: "Gesamtzustand",
      show_guests: "Gäste, die zählen",
      show_visit_end: "Besuchsende",
      show_status: "Status je Gast",
      show_rooms: "Raumsperre und Räume",
      show_unreachable: "Nicht erreichbare Sensoren",
      show_unapproved: "Anzahl der Gäste ohne Freigabe",
      show_visit: "Besuchsende und Restzeit",
      show_guest_rooms: "Offene und geschlossene Räume",
      greeting_text: "Zeile unter der Begrüßung",
      other_rooms_text: "Text für die nicht genannten Räume",
      time_up_text: "Text, wenn die Besuchszeit um ist",
      helpOtherRooms: "Steht bei den offenen Räumen; leer lässt ihn weg.",
    },
  };

  const DEFAULTS = {
    mode: "overview",
    size: "auto",
    show_summary: true,
    show_guests: true,
    show_visit_end: true,
    show_status: true,
    show_rooms: true,
    show_unreachable: false,
    show_unapproved: false,
    show_visit: true,
    show_guest_rooms: true,
  };

  // The language of the last card that got its data, for the editor's labels
  let language = "en";
  const texts = (lang) => TEXTS[(lang || "en").split("-")[0]] || TEXTS.en;
  const fill = (text, values = {}) => text.replace(/\{(\w+)\}/g, (_, key) => String(values[key] ?? ""));
  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  const STYLE = `
    :host { display: block; height: 100%; }
    ha-card { height: 100%; box-sizing: border-box; overflow: hidden; padding: 14px 16px; }
    .content.fill { height: 100%; }
    .head { display: flex; align-items: center; gap: 8px; }
    .head ha-icon { color: var(--secondary-text-color); --mdc-icon-size: 20px; }
    .title { flex: 1; font-size: 16px; font-weight: 500; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .pill { font-size: 12px; padding: 2px 10px; border-radius: 999px; white-space: nowrap;
      background: rgba(var(--rgb-primary-text-color), 0.06); color: var(--secondary-text-color); }
    .pill.only { background: rgba(var(--rgb-info-color), 0.15); color: var(--info-color); }
    .pill.locked { background: rgba(var(--rgb-error-color), 0.15); color: var(--error-color); }
    .pill.free { background: rgba(var(--rgb-success-color), 0.15); color: var(--success-color); }
    .row { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-top: 1px solid var(--divider-color); cursor: pointer; }
    .head + .row, .head + .block, .head + .line { margin-top: 10px; }
    .avatar { width: 36px; height: 36px; border-radius: 50%; flex: none; display: flex; align-items: center; justify-content: center;
      font-weight: 500; font-size: 14px; background: rgba(var(--rgb-success-color), 0.15); color: var(--success-color);
      background-size: cover; background-position: center; }
    .who { flex: 1; min-width: 0; }
    .name { font-size: 14px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .status { font-size: 12px; color: var(--success-color); }
    .status.over { color: var(--warning-color); }
    .end { font-size: 12px; color: var(--secondary-text-color); white-space: nowrap; }
    .end ha-icon { --mdc-icon-size: 14px; margin-right: 2px; }
    .block { padding-top: 10px; border-top: 1px solid var(--divider-color); font-size: 12px; }
    .block .label { display: flex; align-items: center; gap: 8px; color: var(--secondary-text-color); }
    .block .label ha-icon { --mdc-icon-size: 16px; }
    .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
    .line { padding-top: 10px; margin-top: 10px; border-top: 1px solid var(--divider-color); font-size: 12px; color: var(--secondary-text-color); }
    .line.problem { color: var(--warning-color); }
    .line ha-icon { --mdc-icon-size: 16px; margin-right: 6px; }
    .block + .line { margin-top: 10px; }
    .small { display: flex; align-items: center; gap: 10px; height: 100%; }
    .small .avatar { width: 32px; height: 32px; }
    .small .avatar.idle { background: rgba(var(--rgb-primary-text-color), 0.06); color: var(--secondary-text-color); }
    .small .sub { font-size: 12px; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .guest { padding: 10px 6px; }
    .greet { display: flex; align-items: center; gap: 14px; }
    .greet .avatar { width: 56px; height: 56px; font-size: 20px; background-color: rgba(var(--rgb-info-color), 0.15); color: var(--info-color); }
    .greet .hello { font-size: 22px; font-weight: 500; line-height: 1.3; }
    .greet .sub { font-size: 14px; color: var(--secondary-text-color); }
    .visit { margin-top: 18px; padding: 14px 16px; border-radius: var(--ha-card-border-radius, 12px); background: rgba(var(--rgb-primary-text-color), 0.05); }
    .visit .label, .rooms .label { font-size: 13px; color: var(--secondary-text-color); }
    .visit .big { font-size: 24px; font-weight: 500; line-height: 1.3; }
    .visit .left { font-size: 13px; color: var(--secondary-text-color); margin-top: 4px; }
    .visit .each { font-size: 15px; margin-top: 2px; }
    .rooms { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-top: 1px solid var(--divider-color); }
    .visit + .rooms, .greet + .rooms { margin-top: 14px; }
    .rooms ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); }
    .rooms.open ha-icon { color: var(--success-color); }
    .rooms .value { font-size: 15px; }
    .missing { color: var(--secondary-text-color); font-size: 14px; }
  `;

  class GuestAccessCard extends HTMLElement {
    static getStubConfig() {
      return {};
    }

    static getConfigForm() {
      const t = texts(language);
      const bool = (name) => ({ name, selector: { boolean: {} } });
      const text = (name) => ({ name, selector: { text: {} } });
      const pick = (name, options) => ({
        name,
        selector: { select: { mode: "dropdown", options: options.map(([value, label]) => ({ value, label })) } },
      });
      return {
        schema: [
          pick("mode", [["overview", t.modeOverview], ["guest", t.modeGuest]]),
          text("title"),
          pick("size", [["auto", t.sizeAuto], ["small", t.sizeSmall], ["medium", t.sizeMedium], ["large", t.sizeLarge]]),
          {
            type: "expandable",
            name: "overview",
            title: t.sectionOverview,
            flatten: true,
            schema: ["show_summary", "show_guests", "show_visit_end", "show_status", "show_rooms", "show_unreachable", "show_unapproved"].map(bool),
          },
          {
            type: "expandable",
            name: "guest",
            title: t.sectionGuest,
            flatten: true,
            schema: [bool("show_visit"), bool("show_guest_rooms"), text("greeting_text"), text("other_rooms_text"), text("time_up_text")],
          },
        ],
        computeLabel: (field) => texts(language)[field.name] ?? (field.name === "title" ? texts(language).title : field.name),
        computeHelper: (field) => (field.name === "other_rooms_text" ? texts(language).helpOtherRooms : undefined),
      };
    }

    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._config = { ...DEFAULTS };
      this._key = null;
    }

    setConfig(config) {
      this._config = { ...DEFAULTS, ...config };
      this._key = null;
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      language = hass?.language || language;
      this._render();
    }

    // Home Assistant sets it: "grid" in a sections view, where the card has a fixed height
    set layout(layout) {
      this._layout = layout;
      this._key = null;
      this._render();
    }

    getCardSize() {
      return this._config.mode === "guest" ? 6 : 3;
    }

    // As high as what it shows, until someone gives it fewer rows
    getGridOptions() {
      return this._config.mode === "guest"
        ? { columns: 12, rows: "auto", min_columns: 6, min_rows: 2 }
        : { columns: 6, rows: "auto", min_columns: 3, min_rows: 1 };
    }

    connectedCallback() {
      this._observer = new ResizeObserver(() => {
        this._key = null;
        this._render();
      });
      this._observer.observe(this);
      // The time left counts down without a change of any entity
      this._timer = setInterval(() => {
        if (this._config.mode === "guest") {
          this._key = null;
          this._render();
        }
      }, 30000);
      this.shadowRoot.addEventListener("click", (event) => {
        const row = event.target.closest?.("[data-entity]");
        if (!row) return;
        this.dispatchEvent(
          new CustomEvent("hass-more-info", { detail: { entityId: row.dataset.entity }, bubbles: true, composed: true }),
        );
      });
      this._render();
    }

    disconnectedCallback() {
      this._observer?.disconnect();
      clearInterval(this._timer);
    }

    get _t() {
      return texts(this._hass?.language);
    }

    get _lang() {
      return this._hass?.language || "en";
    }

    // In the 12- or 24-hour format of the user's profile, else as the language has it
    _time(iso) {
      const format = this._hass?.locale?.time_format;
      const cycle = format === "12" ? { hourCycle: "h12" } : format === "24" ? { hourCycle: "h23" } : {};
      return new Date(iso).toLocaleTimeString(this._lang, { hour: "2-digit", minute: "2-digit", ...cycle });
    }

    // What the entities say, found by the integration's own keys so that a
    // renamed entity or another language changes nothing
    _data() {
      const hass = this._hass;
      const own = Object.values(hass.entities || {}).filter((entry) => entry.platform === DOMAIN);
      const states = (key) =>
        own
          .filter((entry) => entry.translation_key === key)
          .map((entry) => hass.states[entry.entity_id])
          .filter(Boolean);
      const home = states("guests_home")[0];
      if (!home) return null;
      const guests = (home.attributes.guest_list || [])
        .filter((guest) => PRESENT.includes(guest.status))
        .map((guest) => ({ ...guest, state: hass.states[guest.status_entity] }));
      const rooms = states("room_locked").map((state) => ({
        name: hass.areas?.[state.attributes.area_id]?.name || state.attributes.area_id,
        reason: state.attributes.reason,
      }));
      rooms.sort((a, b) => a.name.localeCompare(b.name, this._lang));
      const unreachable = states("unreachable")[0];
      return {
        guests,
        only: states("only_guests_home")[0]?.state === "on",
        rooms,
        lock: rooms.some((room) => room.reason !== "no_lock"),
        unreachable: unreachable?.state === "on" ? (unreachable.attributes.entities || []).length || 1 : 0,
        unapproved: states("status").filter((state) => ["not_approved", "inactive"].includes(state.state)).length,
      };
    }

    _render() {
      if (!this._hass || !this.isConnected) return;
      const data = this._data();
      const fixed = this._layout === "grid";
      const key = JSON.stringify([data, this._config, this._lang, fixed, this.clientWidth, this.clientHeight, Math.floor(Date.now() / 30000)]);
      if (key === this._key) return;
      this._key = key;
      const root = this.shadowRoot;
      let card = root.querySelector("ha-card");
      if (!card) {
        // The frame stays: a new ha-card shows its content only once it has drawn
        // itself, so what is measured right after creating it would be nothing
        root.innerHTML = `<style>${STYLE}</style><ha-card><div class="content"></div></ha-card>`;
        card = root.querySelector("ha-card");
        card.updateComplete?.then(() => {
          this._key = null;
          this._render();
        });
      }
      const content = root.querySelector(".content");
      // Draws the card and says whether its content is higher than the card
      const draw = (html, fill = false) => {
        content.className = `content${fill ? " fill" : ""}`;
        content.innerHTML = html;
        const style = getComputedStyle(card);
        const room = card.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
        return content.scrollHeight > room + 1;
      };
      if (!data) {
        draw(`<div class="missing">${esc(this._t.missing)}</div>`);
        return;
      }
      const guest = this._config.mode === "guest";
      const wanted = SIZES.includes(this._config.size) ? [this._config.size] : SIZES;
      for (const size of wanted) {
        const overflows = draw(guest ? this._guestView(data, size) : this._overview(data, size), !guest && size === "small");
        // Only a card with a fixed height can be too small for what it shows
        if (!fixed || !overflows) break;
      }
      // A second line that is cut off gives way to a shorter one
      const line = content.querySelector(".sub[data-lines]");
      if (line) {
        // Measured beside the line, to the fraction of a pixel: scrollWidth and
        // clientWidth are whole numbers and call a text that is a hair too wide a fit
        const probe = document.createElement("span");
        probe.className = line.className;
        probe.style.cssText = "position: absolute; visibility: hidden; overflow: visible; width: auto; display: inline-block;";
        line.parentElement.appendChild(probe);
        const room = line.getBoundingClientRect().width;
        for (const text of JSON.parse(line.dataset.lines)) {
          line.textContent = text;
          probe.textContent = text;
          if (probe.getBoundingClientRect().width <= room) break;
        }
        probe.remove();
      }
    }

    _avatar(guest, extra = "") {
      // Only an address on this Home Assistant, as the integration gives it
      const url = /^\/[\w\-./]+$/.test(guest.picture || "") ? guest.picture : null;
      const picture = url ? ` style="background-image: url('${url}')"` : "";
      const letter = url ? "" : esc((guest.name || "?").trim().charAt(0).toUpperCase());
      return `<div class="avatar${extra}"${picture}>${letter}</div>`;
    }

    _summary(data) {
      const t = this._t;
      if (!data.guests.length) return t.nobody;
      if (data.only) return t.onlyGuests;
      return data.guests.length === 1 ? t.guestHome : fill(t.guestsHome, { count: data.guests.length });
    }

    _end(guest) {
      if (guest.status === "time_up") return this._t.timeUp;
      return guest.visit_ends ? fill(this._t.until, { time: this._time(guest.visit_ends) }) : "";
    }

    _overview(data, size) {
      const t = this._t;
      const c = this._config;
      const title = c.title || t.title;
      if (size === "small") {
        const first = data.guests[0];
        const more = data.guests.length - 1;
        const names = !first
          ? title
          : more === 0
            ? first.name
            : fill(more === 1 ? t.andOne : t.andMore, { name: first.name, count: more });
        // A time that is up comes before the earliest end still ahead
        const over = data.guests.some((guest) => guest.status === "time_up");
        const ends = data.guests
          .filter((guest) => guest.status !== "time_up")
          .map((guest) => guest.visit_ends)
          .filter(Boolean)
          .sort();
        const summary = c.show_summary || !first ? this._summary(data) : "";
        const end = !c.show_visit_end ? "" : over ? t.timeUp : ends.length ? fill(t.until, { time: this._time(ends[0]) }) : "";
        // The second line from most to least: where both do not fit, that only guests
        // are home matters more than the time, the time more than a number of guests
        const lines = [[summary, end].filter(Boolean).join(", ")];
        if (summary && end) lines.push(data.only ? summary : end);
        const avatar = first && c.show_guests
          ? this._avatar(first)
          : `<div class="avatar idle"><ha-icon icon="mdi:account-group"></ha-icon></div>`;
        return `<div class="small">${avatar}<div class="who"><div class="name">${esc(c.show_guests ? names : title)}</div>` +
          `<div class="sub" data-lines="${esc(JSON.stringify(lines))}">${esc(lines[0])}</div></div></div>`;
      }
      const large = size === "large";
      let html = `<div class="head"><ha-icon icon="mdi:account-group"></ha-icon><div class="title">${esc(title)}</div>` +
        (c.show_summary ? `<span class="pill${data.only ? " only" : ""}">${esc(this._summary(data))}</span>` : "") + `</div>`;
      if (c.show_guests) {
        for (const guest of data.guests) {
          const over = guest.status === "time_up" || guest.status === "approval_expired";
          const status = large && c.show_status && guest.state
            ? `<div class="status${over ? " over" : ""}">${esc(this._hass.formatEntityState?.(guest.state) ?? guest.status)}</div>`
            : "";
          const end = c.show_visit_end && this._end(guest)
            ? `<span class="end"><ha-icon icon="mdi:clock-outline"></ha-icon>${esc(this._end(guest))}</span>`
            : "";
          html += `<div class="row" data-entity="${esc(guest.status_entity)}">${this._avatar(guest)}` +
            `<div class="who"><div class="name">${esc(guest.name)}</div>${status}</div>${end}</div>`;
        }
      }
      if (!large) return html;
      if (c.show_rooms && data.rooms.length) {
        const chips = data.lock
          ? data.rooms
              .map((room) =>
                room.reason === "locked"
                  ? `<span class="pill locked">${esc(room.name)}</span>`
                  : `<span class="pill free">${esc(fill(room.reason === "open_at_start" ? t.open : t.free, { room: room.name }))}</span>`)
              .join("")
          : "";
        html += `<div class="block"><div class="label"><ha-icon icon="${data.lock ? "mdi:lock" : "mdi:lock-open-variant-outline"}"></ha-icon>` +
          `${esc(data.lock ? t.lockActive : t.noLock)}</div>${chips ? `<div class="chips">${chips}</div>` : ""}</div>`;
      }
      if (c.show_unreachable && data.unreachable) {
        html += `<div class="line problem"><ha-icon icon="mdi:alert-outline"></ha-icon>` +
          `${esc(data.unreachable === 1 ? t.unreachableOne : fill(t.unreachableMany, { count: data.unreachable }))}</div>`;
      }
      if (c.show_unapproved && data.unapproved) {
        html += `<div class="line">${esc(data.unapproved === 1 ? t.unapprovedOne : fill(t.unapprovedMany, { count: data.unapproved }))}</div>`;
      }
      return html;
    }

    _left(iso) {
      const t = this._t;
      const minutes = Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 60000));
      if (minutes === 1) return t.minuteLeft;
      if (minutes < 90) return fill(t.minutesLeft, { minutes });
      return fill(t.hoursLeft, { hours: Math.floor(minutes / 60), minutes: minutes % 60 });
    }

    // For the guests themselves: who is welcome, until when, and which doors stay shut
    _guestView(data, size) {
      const t = this._t;
      const c = this._config;
      const guests = data.guests;
      const names = guests.map((guest) => guest.name);
      const list = names.length > 1 ? `${names.slice(0, -1).join(", ")} ${t.and} ${names[names.length - 1]}` : names[0];
      const greeting = c.greeting_text ?? (guests.length > 1 ? t.greetingMany : t.greetingOne);
      let html = `<div class="guest"><div class="greet">${guests.length === 1 ? this._avatar(guests[0]) : ""}<div>` +
        `<div class="hello">${esc(guests.length ? fill(t.welcomeNames, { names: list }) : t.welcome)}</div>` +
        (size !== "small" && greeting ? `<div class="sub">${esc(greeting)}</div>` : "") + `</div></div>`;
      if (c.show_visit && guests.length) {
        const over = c.time_up_text ?? t.timeUpText;
        if (guests.length === 1) {
          const guest = guests[0];
          if (guest.status === "time_up") {
            html += `<div class="visit"><div class="label">${esc(t.yourVisit)}</div><div class="each">${esc(over)}</div></div>`;
          } else if (guest.visit_ends) {
            html += `<div class="visit"><div class="label">${esc(t.yourVisit)}</div>` +
              `<div class="big">${esc(fill(t.visitUntil, { time: this._time(guest.visit_ends) }))}</div>` +
              (size !== "small" ? `<div class="left">${esc(this._left(guest.visit_ends))}</div>` : "") + `</div>`;
          }
        } else {
          const lines = guests
            .filter((guest) => guest.status === "time_up" || guest.visit_ends)
            .map((guest) =>
              `<div class="each">${esc(guest.name)}: ${esc(guest.status === "time_up" ? over : fill(t.visitUntil, { time: this._time(guest.visit_ends) }))}</div>`);
          if (lines.length) html += `<div class="visit">${lines.join("")}</div>`;
        }
      }
      if (c.show_guest_rooms && size === "large" && data.lock) {
        const free = data.rooms.filter((room) => room.reason === "guest_may_enter").map((room) => room.name);
        const closed = data.rooms.filter((room) => room.reason === "locked").map((room) => room.name);
        const other = c.other_rooms_text ?? t.otherRooms;
        const open = free.length && other ? `${free.join(", ")} ${t.and} ${other}` : free.join(", ") || other.charAt(0).toUpperCase() + other.slice(1);
        if (open) {
          html += `<div class="rooms open"><ha-icon icon="mdi:door-open"></ha-icon><div><div class="label">${esc(t.openForYou)}</div>` +
            `<div class="value">${esc(open)}</div></div></div>`;
        }
        if (closed.length) {
          html += `<div class="rooms"><ha-icon icon="mdi:door-closed"></ha-icon><div><div class="label">${esc(t.keepClosed)}</div>` +
            `<div class="value">${esc(closed.join(", "))}</div></div></div>`;
        }
      }
      return `${html}</div>`;
    }
  }

  if (!customElements.get(TAG)) customElements.define(TAG, GuestAccessCard);
  window.customCards = window.customCards || [];
  if (!window.customCards.some((card) => card.type === TAG)) {
    window.customCards.push({ type: TAG, name: TEXTS.en.name, description: TEXTS.en.description, preview: true });
  }
})();

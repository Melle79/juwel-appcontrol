/*
 * Juwel HeliaLux Card  v2.0.0
 * Lovelace card for the "juwel_appcontrol" integration.
 *
 * Options (all available in the visual editor):
 *   design : "juwel" (MyJUWEL look) | "ha" (follow the Home Assistant theme)
 *   layout : "full"  (curve, profile, switch, sliders) | "compact" (single row)
 *   tap_action : "popup" | "more-info" | "hash" | "none"
 *
 * UI strings are English by default and translated to German automatically.
 */

const CH = [
  { key: "white", label: "W", names: ["White", "Weiß"], color: "#ffffff" },
  { key: "red", label: "R", names: ["Red", "Rot"], color: "#e2574c" },
  { key: "green", label: "G", names: ["Green", "Grün"], color: "#3fbf6f" },
  { key: "blue", label: "B", names: ["Blue", "Blau"], color: "#3d7fe3" },
];

/* UI strings: English base, German translation */
const I18N = {
  en: {
    status: "Status", online: "Online", offline: "Offline",
    profile: "Profile", manual: "Manual mode",
    autoHint: "Sliders are locked while the schedule is running — use the switch above.",
    notFound: "Entity not found",
    fLight: "Light entity (Juwel HeliaLux)", fName: "Heading (optional)",
    fLayout: "Appearance", fDesign: "Design", fChart: "Show daily curve",
    fTap: "On tap", fHash: "Hash of the Bubble Card pop-up (e.g. #aquarium)",
    oFull: "Full (curve, profile, sliders)", oCompact: "Compact (single row)",
    oJuwel: "MyJUWEL look (dark blue)", oHa: "Follow Home Assistant theme",
    oPopup: "Open the full card as a pop-up", oMore: "Show more-info dialog",
    oHash: "Open a Bubble Card pop-up by hash", oNone: "Do nothing",
    plan: "Plan", feedNow: "Feed now", feeding: "Feeding…",
    quantity: "Quantity", statusLed: "Status LED",
    chamber: "Feed chamber", chamberEmpty: "Empty", chamberOk: "Filled",
    motor: "Auger", lastFeed: "Last feeding", never: "never",
    noPlan: "no plan", amount: "amount", fFeeder: "Feeder (Juwel AppControl)",
  },
  de: {
    status: "Status", online: "Online", offline: "Offline",
    profile: "Profil", manual: "Manueller Modus",
    autoHint: "Im Automatikmodus sind die Regler gesperrt – Schalter oben umlegen.",
    notFound: "Entität nicht gefunden",
    fLight: "Licht-Entität (Juwel HeliaLux)", fName: "Überschrift (optional)",
    fLayout: "Darstellung", fDesign: "Design", fChart: "Tageskurve anzeigen",
    fTap: "Beim Antippen", fHash: "Hash des Bubble-Card-Popups (z. B. #aquarium)",
    oFull: "Vollständig (Kurve, Profil, Regler)", oCompact: "Kompakt (eine Zeile)",
    oJuwel: "MyJUWEL-Look (dunkelblau)", oHa: "Home-Assistant-Theme übernehmen",
    oPopup: "Große Karte als Popup öffnen", oMore: "Detailansicht (more-info)",
    oHash: "Bubble-Card-Popup per Hash öffnen", oNone: "Nichts tun",
    plan: "Plan", feedNow: "Jetzt füttern", feeding: "Füttert…",
    quantity: "Menge", statusLed: "Status-LED",
    chamber: "Futterkammer", chamberEmpty: "Leer", chamberOk: "Gefüllt",
    motor: "Futterschnecke", lastFeed: "Letzte Fütterung", never: "nie",
    noPlan: "kein Plan", amount: "Menge", fFeeder: "Futterautomat (Juwel AppControl)",
  },
};

const t = (hass) => {
  const lang = (hass && (hass.language || (hass.locale || {}).language)) || "en";
  return I18N[lang.split("-")[0]] || I18N.en;
};

class JuwelHelialuxCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._dragging = null;
  }

  static getConfigElement() {
    return document.createElement("juwel-helialux-card-editor");
  }

  static getStubConfig(hass) {
    const light = Object.keys(hass.states).find((e) => e.startsWith("light."));
    return { light: light || "", design: "juwel", layout: "full", show_chart: true };
  }

  setConfig(config) {
    if (!config.light && !config.entity) {
      throw new Error("Please choose a light entity of the Juwel HeliaLux integration.");
    }
    this._config = {
      design: "juwel",
      layout: "full",
      show_chart: true,
      // Kompakt öffnet standardmäßig die große Karte als Popup
      tap_action: config.layout === "compact" ? "popup" : "none",
      ...config,
    };
    this._lightId = config.light || config.entity;
    this._built = false;
  }

  getCardSize() {
    if (!this._config) return 5;
    if (this._config.layout === "compact") return 1;
    return this._config.show_chart ? 9 : 5;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return; // hass kann vor setConfig kommen
    this._resolve();
    this._render();
    // geöffnetes Popup mitversorgen, damit es live bleibt
    if (this._popupCard) this._popupCard.hass = hass;
  }

  /* ---------- Entitäten des Geräts finden ---------- */
  _resolve() {
    const hass = this._hass;
    const c = this._config;
    this._ids = { light: this._lightId };

    const reg = hass.entities || {};
    const devId = reg[this._lightId] && reg[this._lightId].device_id;
    const siblings = devId
      ? Object.keys(reg).filter((e) => reg[e].device_id === devId)
      : [];

    const fname = (e) =>
      (hass.states[e] && hass.states[e].attributes.friendly_name) || "";

    this._ids.preset = c.preset_sensor || siblings.find((e) => e.startsWith("sensor."));

    // Bevorzugt: der Profil-Sensor nennt die Geschwister-Entitäten selbst
    const sa = (this._ids.preset && hass.states[this._ids.preset]
      ? hass.states[this._ids.preset].attributes
      : {}) || {};
    const chMap = sa.channel_entities || {};

    this._ids.auto =
      c.auto_switch || sa.auto_switch_entity ||
      siblings.find((e) => e.startsWith("switch."));

    CH.forEach((ch) => {
      this._ids[ch.key] =
        c[ch.key] ||
        chMap[ch.key] ||
        // Rückfall: über den Anzeigenamen (EN/DE)
        siblings.find(
          (e) =>
            e.startsWith("number.") &&
            ch.names.some((n) => fname(e).endsWith(n))
        );
    });
  }

  _st(id) {
    return id && this._hass.states[id];
  }

  /* ---------- Aufbau ---------- */
  _build() {
    this.shadowRoot.innerHTML = `
      <style>
        /* Farbschema: wird je nach "design" auf :host gesetzt */
        :host{
          --jh-bg:#0b2239; --jh-fg:#ffffff; --jh-sub:rgba(255,255,255,.85);
          --jh-row:#12314f; --jh-grid:rgba(255,255,255,.13);
          --jh-track:rgba(255,255,255,.12); --jh-swoff:#0d1b2a; --jh-swon:#2b6cb0;
          --jh-bubble:#17416b; --jh-radius:22px;
        }
        :host([data-design="ha"]){
          --jh-bg:var(--ha-card-background, var(--card-background-color, #fff));
          --jh-fg:var(--primary-text-color);
          --jh-sub:var(--secondary-text-color);
          --jh-row:var(--secondary-background-color, rgba(127,127,127,.12));
          --jh-grid:var(--divider-color, rgba(127,127,127,.3));
          --jh-track:var(--divider-color, rgba(127,127,127,.25));
          --jh-swoff:var(--switch-unchecked-track-color, rgba(127,127,127,.4));
          --jh-swon:var(--primary-color);
          --jh-bubble:var(--primary-color);
          --jh-radius:var(--ha-card-border-radius, 12px);
        }
        ha-card{
          background:var(--jh-bg); color:var(--jh-fg);
          border-radius:var(--jh-radius); overflow:hidden;
        }
        .full{padding:16px 18px 20px}
        .compact{padding:12px 14px;display:flex;align-items:center;gap:12px;cursor:pointer}

        .head{display:flex;align-items:center;gap:12px;margin-bottom:4px}
        .icon{width:34px;height:34px;flex:0 0 auto;opacity:.9;color:var(--jh-fg)}
        .title{font-size:1.25rem;font-weight:600;line-height:1.2}
        .status{font-size:.85rem;color:var(--jh-sub)}
        .ok{color:#41d07e;font-weight:600}.bad{color:#ff6b6b;font-weight:600}
        .chart{margin:10px 0 4px}
        svg{width:100%;height:auto;display:block}
        .prow{background:var(--jh-row);border-radius:16px;padding:10px 14px;
              display:flex;align-items:center;gap:12px;margin-top:14px}
        .dot{width:34px;height:34px;border-radius:50%;flex:0 0 auto;background:#b5d4e3}
        .plabel{font-weight:600}
        .toggle-row{display:flex;align-items:center;gap:14px;margin:16px 2px 6px}
        .sw{width:56px;height:30px;border-radius:15px;background:var(--jh-swoff);
            position:relative;cursor:pointer;flex:0 0 auto;transition:background .2s;
            border:1px solid var(--jh-grid)}
        .sw.on{background:var(--jh-swon)}
        .knob{position:absolute;top:3px;left:3px;width:22px;height:22px;border-radius:50%;
              background:#fff;transition:left .2s;box-shadow:0 1px 3px rgba(0,0,0,.4)}
        .sw.on .knob{left:29px}
        .toggle-label{font-weight:600}
        .sliders{margin-top:10px}
        .sl{display:flex;align-items:center;gap:12px;margin:14px 2px}
        .sl .lab{width:16px;color:var(--jh-sub);font-weight:600}
        .track{position:relative;flex:1;height:14px;border-radius:7px;cursor:pointer;
               background:var(--jh-track)}
        .fillbg{position:absolute;inset:0;border-radius:7px;opacity:.28}
        .fill{position:absolute;top:0;bottom:0;left:0;border-radius:7px;opacity:.95}
        .grip{position:absolute;top:50%;width:26px;height:26px;border-radius:50%;
              background:#fff;transform:translate(-50%,-50%);
              box-shadow:0 1px 4px rgba(0,0,0,.45)}
        .val{width:52px;text-align:right;font-variant-numeric:tabular-nums}
        .disabled{opacity:.45;pointer-events:none}
        .hint{font-size:.78rem;color:var(--jh-sub);opacity:.8;margin:8px 2px 0}
        .err{padding:16px;color:#ff8a8a}

        /* --- kompakte Variante --- */
        .c-name{font-weight:600;flex:0 1 auto;white-space:nowrap;overflow:hidden;
                text-overflow:ellipsis}
        .c-vals{margin-left:auto;display:flex;align-items:center;gap:10px}
        .chip{display:flex;align-items:center;gap:5px;font-variant-numeric:tabular-nums;
              font-size:.95rem}
        .swatch{width:10px;height:10px;border-radius:50%;flex:0 0 auto;
                box-shadow:0 0 0 1px var(--jh-grid)}
        .c-off{opacity:.45}
      </style>
      <ha-card><div id="body"></div></ha-card>`;
    this._built = true;
  }

  /* ---------- Zeichnen ---------- */
  _render() {
    if (!this._hass || !this._config) return;
    if (!this._built) this._build();
    this.setAttribute("data-design", this._config.design === "ha" ? "ha" : "juwel");

    const T = t(this._hass);
    const body = this.shadowRoot.getElementById("body");
    const light = this._st(this._ids.light);
    if (!light) {
      body.innerHTML = `<div class="err">${T.notFound}: <code>${this._lightId}</code></div>`;
      return;
    }

    const preset = this._st(this._ids.preset);
    const autoSw = this._st(this._ids.auto);
    const attrs = (preset && preset.attributes) || {};
    const online = attrs.connected !== false && light.state !== "unavailable";
    const isAuto = autoSw ? autoSw.state === "on" : attrs.mode === "auto";
    const name = this._config.name || light.attributes.friendly_name || "HeliaLux";

    if (this._config.layout === "compact") {
      body.className = "compact";
      body.innerHTML = `
        <div class="c-name">${name}</div>
        <div class="c-vals ${online ? "" : "c-off"}">
          ${CH.map((ch) => {
            const st = this._st(this._ids[ch.key]);
            const v = st ? Math.round(Number(st.state)) : 0;
            return `<div class="chip">
                      <span class="swatch" style="background:${ch.color}"></span>${isNaN(v) ? 0 : v} %
                    </div>`;
          }).join("")}
        </div>`;
      body.onclick = () => this._handleTap();
      return;
    }

    body.className = "full";
    body.onclick = null;
    const chart = this._config.show_chart
      ? `<div class="chart">${this._chartSvg(attrs.time_events || [])}</div>`
      : "";

    body.innerHTML = `
      <div class="head">
        <svg class="icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M6 2h12a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm2 3v2h2V5H8zm4 0v2h2V5h-2zM8 9v2h2V9H8zm4 0v2h2V9h-2zm-4 4v2h2v-2H8zm4 0v2h2v-2h-2zm-4 4v2h2v-2H8zm4 0v2h2v-2h-2z"/>
        </svg>
        <div>
          <div class="title">${name}</div>
          <div class="status">${T.status}:
            <span class="${online ? "ok" : "bad"}">${online ? T.online : T.offline}</span>
          </div>
        </div>
      </div>
      ${chart}
      <div class="prow">
        <div class="dot" style="background:${attrs.preset_color || "#b5d4e3"}"></div>
        <div class="plabel">${T.profile}: ${preset ? preset.state : "–"}</div>
      </div>
      <div class="toggle-row">
        <div class="sw ${isAuto ? "" : "on"}" id="manual"><div class="knob"></div></div>
        <div class="toggle-label">${T.manual}</div>
      </div>
      <div class="sliders ${isAuto ? "disabled" : ""}">
        ${CH.map((ch) => this._sliderHtml(ch)).join("")}
      </div>
      ${isAuto ? `<div class="hint">${T.autoHint}</div>` : ""}`;

    this._wire();
  }

  _moreInfo(entityId) {
    if (!entityId) return;
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      })
    );
  }

  /* ---------- Tipp-Aktion ---------- */
  _handleTap() {
    switch (this._config.tap_action) {
      case "more-info":
        this._moreInfo(this._ids.light);
        break;
      case "hash": {
        // Bubble-Card-Popup: per Hash in der URL öffnen
        const h = this._config.popup_hash || "#aquarium";
        const hash = h.startsWith("#") ? h : "#" + h;
        history.pushState(null, "", location.pathname + location.search + hash);
        window.dispatchEvent(new Event("location-changed"));
        break;
      }
      case "none":
        break;
      default:
        this._openPopup();
    }
  }

  /* Große Karte als Popup-Dialog */
  _openPopup() {
    if (this._dialog) return;
    const dlg = document.createElement("ha-dialog");
    dlg.setAttribute("hideactions", "");
    dlg.heading =
      this._config.name ||
      (this._st(this._ids.light) || {}).attributes?.friendly_name ||
      "HeliaLux";
    dlg.style.setProperty("--dialog-content-padding", "0");
    dlg.style.setProperty("--mdc-dialog-min-width", "min(94vw, 420px)");
    dlg.style.setProperty("--mdc-dialog-max-width", "min(94vw, 480px)");

    const card = document.createElement("juwel-helialux-card");
    card.setConfig({
      ...this._config,
      layout: "full",
      tap_action: "none",
    });
    card.hass = this._hass;
    dlg.appendChild(card);

    dlg.addEventListener("closed", () => {
      dlg.remove();
      this._dialog = null;
      this._popupCard = null;
    });

    document.body.appendChild(dlg);
    this._dialog = dlg;
    this._popupCard = card;
    dlg.open = true;
  }

  _sliderHtml(ch) {
    const st = this._st(this._ids[ch.key]);
    const raw = st ? Math.round(Number(st.state)) : 0;
    const pct = isNaN(raw) ? 0 : Math.max(0, Math.min(100, raw));
    return `
      <div class="sl" data-ch="${ch.key}">
        <div class="lab">${ch.label}</div>
        <div class="track" data-ch="${ch.key}">
          <div class="fillbg" style="background:${ch.color}"></div>
          <div class="fill" style="width:${pct}%;background:${ch.color}"></div>
          <div class="grip" style="left:${pct}%"></div>
        </div>
        <div class="val">${pct} %</div>
      </div>`;
  }

  /* ---------- Tageskurve ---------- */
  _chartSvg(events) {
    const W = 340, H = 150, L = 34, R = 6, T = 8, B = 20;
    const pw = W - L - R, ph = H - T - B;
    const x = (min) => L + (min / 1440) * pw;
    const y = (v) => T + ph - (Math.max(0, Math.min(100, v)) / 100) * ph;
    const dark = this._config.design !== "ha";
    const axis = dark ? "#ffffff" : "currentColor";

    let lines = "";
    if (events.length) {
      const pts = [...events].sort((a, b) => a.time - b.time);
      lines = CH.map((ch) => {
        const seq = pts.map((p) => [x(p.time), y(p[ch.key] || 0)]);
        const first = pts[0], last = pts[pts.length - 1];
        seq.unshift([x(0), y(last[ch.key] || 0)]);
        seq.push([x(1440), y(first[ch.key] || 0)]);
        const stroke = ch.key === "white" && !dark ? "#9aa0a6" : ch.color;
        return `<polyline points="${seq.map((p) => p.join(",")).join(" ")}" fill="none"
                  stroke="${stroke}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
      }).join("");
    }

    let grid = "";
    [25, 50, 75, 100].forEach((v) => {
      grid += `<line x1="${L}" y1="${y(v)}" x2="${W - R}" y2="${y(v)}" stroke="${axis}" opacity=".2"/>
               <text x="${L - 5}" y="${y(v) + 3.5}" fill="${axis}" opacity=".75" font-size="8" text-anchor="end">${v}%</text>`;
    });
    let xlab = "";
    [0, 360, 720, 1080, 1440].forEach((m) => {
      const h = String(m / 60).padStart(2, "0");
      xlab += `<text x="${x(m)}" y="${H - 6}" fill="${axis}" opacity=".75" font-size="8" text-anchor="middle">${h}:00</text>`;
    });

    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();
    const nx = x(nowMin);
    const label = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    const bx = Math.min(Math.max(nx - 18, L), W - R - 36);
    const nowMark = `
      <line x1="${nx}" y1="${T}" x2="${nx}" y2="${T + ph}" stroke="${axis}" opacity=".85"/>
      <circle cx="${nx}" cy="${T + ph}" r="3" fill="${axis}"/>
      <rect x="${bx}" y="${T - 6}" width="36" height="14" rx="7" fill="var(--jh-bubble)"/>
      <text x="${bx + 18}" y="${T + 4}" fill="#fff" font-size="8" text-anchor="middle">${label}</text>`;

    return `<svg viewBox="0 0 ${W} ${H}" style="color:var(--jh-fg)" preserveAspectRatio="xMidYMid meet">
      ${grid}${lines}${nowMark}${xlab}</svg>`;
  }

  /* ---------- Interaktion ---------- */
  _wire() {
    const man = this.shadowRoot.getElementById("manual");
    if (man) {
      man.onclick = () => {
        const sw = this._ids.auto;
        if (!sw) return;
        const isAuto = this._hass.states[sw].state === "on";
        this._hass.callService("switch", isAuto ? "turn_off" : "turn_on", { entity_id: sw });
      };
    }

    this.shadowRoot.querySelectorAll(".track").forEach((tr) => {
      const key = tr.dataset.ch;
      const apply = (ev) => {
        const rect = tr.getBoundingClientRect();
        const cx = (ev.touches ? ev.touches[0].clientX : ev.clientX) - rect.left;
        const pct = Math.round(Math.max(0, Math.min(1, cx / rect.width)) * 100);
        tr.querySelector(".fill").style.width = pct + "%";
        tr.querySelector(".grip").style.left = pct + "%";
        const v = tr.parentElement.querySelector(".val");
        if (v) v.textContent = pct + " %";
        return pct;
      };
      tr.onpointerdown = (e) => {
        tr.setPointerCapture(e.pointerId);
        this._dragging = key;
        apply(e);
      };
      tr.onpointermove = (e) => {
        if (this._dragging === key) apply(e);
      };
      tr.onpointerup = (e) => {
        if (this._dragging !== key) return;
        const pct = apply(e);
        this._dragging = null;
        const ent = this._ids[key];
        if (ent) this._hass.callService("number", "set_value", { entity_id: ent, value: pct });
      };
    });
  }
}

/* ---------------- UI-Editor ---------------- */
class JuwelHelialuxCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { design: "juwel", layout: "full", show_chart: true, ...config };
    this._render();
  }
  set hass(hass) {
    this._hass = hass;
    this._render();
  }
  _render() {
    // hass kann vor setConfig gesetzt werden -> beides muss da sein
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        this._config = ev.detail.value;
        this.dispatchEvent(
          new CustomEvent("config-changed", { detail: { config: this._config } })
        );
      });
      this.appendChild(this._form);
    }
    const compact = this._config.layout === "compact";
    const T = t(this._hass);
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = [
      {
        name: "light",
        required: true,
        selector: { entity: { domain: "light", integration: "juwel_appcontrol" } },
      },
      { name: "name", selector: { text: {} } },
      {
        name: "layout",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "full", label: T.oFull },
              { value: "compact", label: T.oCompact },
            ],
          },
        },
      },
      {
        name: "design",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "juwel", label: T.oJuwel },
              { value: "ha", label: T.oHa },
            ],
          },
        },
      },
      ...(compact ? [] : [{ name: "show_chart", selector: { boolean: {} } }]),
      {
        name: "tap_action",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "popup", label: T.oPopup },
              { value: "more-info", label: T.oMore },
              { value: "hash", label: T.oHash },
              { value: "none", label: T.oNone },
            ],
          },
        },
      },
      ...(this._config.tap_action === "hash"
        ? [{ name: "popup_hash", selector: { text: {} } }]
        : []),
    ];
    this._form.computeLabel = (s) =>
      ({
        light: T.fLight,
        name: T.fName,
        layout: T.fLayout,
        design: T.fDesign,
        show_chart: T.fChart,
        tap_action: T.fTap,
        popup_hash: T.fHash,
      }[s.name] || s.name);
  }
}

// Doppelt-Laden abfangen (z. B. alter Ressourcen-Eintrag + Auto-Registrierung)
if (!customElements.get("juwel-helialux-card")) {
  customElements.define("juwel-helialux-card", JuwelHelialuxCard);
}
if (!customElements.get("juwel-helialux-card-editor")) {
  customElements.define("juwel-helialux-card-editor", JuwelHelialuxCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "juwel-helialux-card"))
window.customCards.push({
  type: "juwel-helialux-card",
  name: "Juwel HeliaLux",
  description: "Aquarium light: daily curve, profile and W/R/G/B — full or compact",
  preview: true,
  documentationURL: "https://github.com/Melle79/juwel-helialux",
});

console.info("%c JUWEL-HELIALUX-CARD %c v2.0.0 ", "background:#0b2239;color:#fff", "background:#2b6cb0;color:#fff");

/* ======================================================================
 *  Juwel Feeder Card  —  SmartFeed AppControl
 *  Reads its sibling entities from the feeding-plan sensor's attributes,
 *  so discovery does not depend on entity names or the UI language.
 * ==================================================================== */

class JuwelFeederCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  static getConfigElement() {
    return document.createElement("juwel-feeder-card-editor");
  }

  static getStubConfig(hass) {
    const s = Object.keys(hass.states).find(
      (e) => e.startsWith("sensor.") && hass.states[e].attributes.feed_button
    );
    return { plan_sensor: s || "", design: "juwel", layout: "full" };
  }

  setConfig(config) {
    if (!config.plan_sensor && !config.entity) {
      throw new Error("Please choose the feeding plan sensor of your SmartFeed.");
    }
    this._config = { design: "juwel", layout: "full", tap_action: "popup", ...config };
    this._anchor = config.plan_sensor || config.entity;
    this._built = false;
  }

  getCardSize() {
    if (!this._config) return 4;
    return this._config.layout === "compact" ? 1 : 5;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    this._render();
    if (this._popupCard) this._popupCard.hass = hass;
  }

  _st(id) {
    return id && this._hass.states[id];
  }

  _ids() {
    const a = (this._st(this._anchor) || {}).attributes || {};
    return {
      plan: this._anchor,
      feed: a.feed_button,
      qty: a.quantity_entity,
      led: a.led_entity,
      power: a.power_entity,
      chamber: a.chamber_entity,
      error: a.error_entity,
      motor: a.motor_entity,
      last: a.last_feed_entity,
    };
  }

  _build() {
    this.shadowRoot.innerHTML = `
      <style>
        :host{
          --jh-bg:#0b2239; --jh-fg:#ffffff; --jh-sub:rgba(255,255,255,.85);
          --jh-row:#12314f; --jh-grid:rgba(255,255,255,.13);
          --jh-track:rgba(255,255,255,.12); --jh-swoff:#0d1b2a; --jh-swon:#2b6cb0;
          --jh-accent:#2b6cb0; --jh-radius:22px;
        }
        :host([data-design="ha"]){
          --jh-bg:var(--ha-card-background, var(--card-background-color, #fff));
          --jh-fg:var(--primary-text-color);
          --jh-sub:var(--secondary-text-color);
          --jh-row:var(--secondary-background-color, rgba(127,127,127,.12));
          --jh-grid:var(--divider-color, rgba(127,127,127,.3));
          --jh-track:var(--divider-color, rgba(127,127,127,.25));
          --jh-swoff:var(--switch-unchecked-track-color, rgba(127,127,127,.4));
          --jh-swon:var(--primary-color); --jh-accent:var(--primary-color);
          --jh-radius:var(--ha-card-border-radius, 12px);
        }
        ha-card{background:var(--jh-bg);color:var(--jh-fg);
                border-radius:var(--jh-radius);overflow:hidden}
        .full{padding:16px 18px 20px}
        .compact{padding:12px 14px;display:flex;align-items:center;gap:12px;cursor:pointer}
        .head{display:flex;align-items:center;gap:12px;margin-bottom:6px}
        .icon{width:32px;height:32px;flex:0 0 auto;opacity:.9;color:var(--jh-fg)}
        .title{font-size:1.2rem;font-weight:600;line-height:1.2}
        .status{font-size:.85rem;color:var(--jh-sub)}
        .ok{color:#41d07e;font-weight:600}.bad{color:#ff6b6b;font-weight:600}
        .prow{background:var(--jh-row);border-radius:16px;padding:10px 14px;margin-top:12px}
        .plan{font-weight:600}
        .times{font-size:.85rem;color:var(--jh-sub);margin-top:3px}
        .feed{
          width:100%;margin-top:14px;padding:14px;border:0;border-radius:16px;
          background:var(--jh-accent);color:#fff;font-size:1.05rem;font-weight:600;
          cursor:pointer;font-family:inherit;
        }
        .feed:active{filter:brightness(.9)}
        .feed[disabled]{opacity:.6;cursor:default}
        .sl{display:flex;align-items:center;gap:12px;margin:16px 2px 4px}
        .sl .lab{color:var(--jh-sub);min-width:58px}
        .track{position:relative;flex:1;height:14px;border-radius:7px;cursor:pointer;
               background:var(--jh-track)}
        .fill{position:absolute;top:0;bottom:0;left:0;border-radius:7px;
              background:var(--jh-accent);opacity:.95}
        .grip{position:absolute;top:50%;width:24px;height:24px;border-radius:50%;
              background:#fff;transform:translate(-50%,-50%);box-shadow:0 1px 4px rgba(0,0,0,.45)}
        .val{width:28px;text-align:right;font-variant-numeric:tabular-nums}
        .toggle-row{display:flex;align-items:center;gap:14px;margin:14px 2px 2px}
        .sw{width:52px;height:28px;border-radius:14px;background:var(--jh-swoff);
            position:relative;cursor:pointer;flex:0 0 auto;border:1px solid var(--jh-grid)}
        .sw.on{background:var(--jh-swon)}
        .knob{position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;
              background:#fff;transition:left .2s}
        .sw.on .knob{left:27px}
        .facts{margin-top:14px;border-top:1px solid var(--jh-grid);padding-top:10px}
        .fact{display:flex;justify-content:space-between;font-size:.9rem;margin:6px 0}
        .fact .k{color:var(--jh-sub)}
        .warn{color:#ffb020;font-weight:600}
        .c-vals{margin-left:auto;display:flex;align-items:center;gap:12px;font-size:.95rem}
        .c-name{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .err{padding:16px;color:#ff8a8a}
      </style>
      <ha-card><div id="body"></div></ha-card>`;
    this._built = true;
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._built) this._build();
    this.setAttribute("data-design", this._config.design === "ha" ? "ha" : "juwel");
    const T = t(this._hass);
    const body = this.shadowRoot.getElementById("body");
    const ids = this._ids();
    const plan = this._st(ids.plan);

    if (!plan) {
      body.innerHTML = `<div class="err">${T.notFound}: <code>${this._anchor}</code></div>`;
      return;
    }

    const a = plan.attributes || {};
    const name = this._config.name || (a.friendly_name || "").replace(/\s*\S+$/, "") ||
                 plan.attributes.friendly_name || "SmartFeed";
    const chamber = this._st(ids.chamber);
    const empty = chamber && chamber.state === "on";
    const motor = this._st(ids.motor);
    const busy = motor && motor.state === "running";
    const last = this._st(ids.last);
    const online = plan.state !== "unavailable";

    const lastTxt = last && last.state && last.state !== "unknown"
      ? new Date(last.state).toLocaleString(this._hass.language || "en",
          { dateStyle: "short", timeStyle: "short" })
      : T.never;

    if (this._config.layout === "compact") {
      body.className = "compact";
      body.innerHTML = `
        <div class="c-name">${name}</div>
        <div class="c-vals">
          ${empty ? `<span class="warn">${T.chamberEmpty}</span>` : ""}
          <span>${lastTxt}</span>
        </div>`;
      body.onclick = () => this._tap();
      return;
    }

    body.className = "full";
    body.onclick = null;
    const times = (a.feedings || [])
      .map((f) => `${f.time} · ${T.amount} ${f.amount}`)
      .join("   •   ");

    body.innerHTML = `
      <div class="head">
        <svg class="icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 4c4.4 0 8 3.1 8 7s-3.6 7-8 7c-1.7 0-3.3-.5-4.6-1.3L4 18l1.2-3A6.6 6.6 0 0 1 4 11c0-3.9 3.6-7 8-7zm4 6a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/>
        </svg>
        <div>
          <div class="title">${name}</div>
          <div class="status">${T.status}:
            <span class="${online ? "ok" : "bad"}">${online ? T.online : T.offline}</span>
          </div>
        </div>
      </div>

      <div class="prow">
        <div class="plan">${T.plan}: ${plan.state === "none" ? T.noPlan : plan.state}</div>
        ${times ? `<div class="times">${times}${a.weekdays_text ? "   •   " + a.weekdays_text : ""}</div>` : ""}
      </div>

      <button class="feed" id="feed" ${busy || !ids.feed ? "disabled" : ""}>
        ${busy ? T.feeding : T.feedNow}
      </button>

      ${ids.qty ? this._slider(T, ids.qty) : ""}
      ${ids.led ? this._toggle(T, ids.led) : ""}

      <div class="facts">
        <div class="fact"><span class="k">${T.chamber}</span>
          <span class="${empty ? "warn" : ""}">${empty ? T.chamberEmpty : T.chamberOk}</span></div>
        ${motor ? `<div class="fact"><span class="k">${T.motor}</span><span>${motor.state}</span></div>` : ""}
        <div class="fact"><span class="k">${T.lastFeed}</span><span>${lastTxt}</span></div>
      </div>`;

    this._wire(ids);
  }

  _slider(T, entityId) {
    const st = this._st(entityId);
    const min = (st && st.attributes.min) || 1;
    const max = (st && st.attributes.max) || 8;
    const val = st ? Number(st.state) : min;
    const pct = ((val - min) / Math.max(1, max - min)) * 100;
    return `
      <div class="sl">
        <div class="lab">${T.quantity}</div>
        <div class="track" id="qty" data-min="${min}" data-max="${max}">
          <div class="fill" style="width:${pct}%"></div>
          <div class="grip" style="left:${pct}%"></div>
        </div>
        <div class="val" id="qtyval">${val}</div>
      </div>`;
  }

  _toggle(T, entityId) {
    const on = (this._st(entityId) || {}).state === "on";
    return `
      <div class="toggle-row">
        <div class="sw ${on ? "on" : ""}" id="led"><div class="knob"></div></div>
        <div>${T.statusLed}</div>
      </div>`;
  }

  _wire(ids) {
    const feed = this.shadowRoot.getElementById("feed");
    if (feed && ids.feed) {
      feed.onclick = () =>
        this._hass.callService("button", "press", { entity_id: ids.feed });
    }

    const led = this.shadowRoot.getElementById("led");
    if (led && ids.led) {
      led.onclick = () => {
        const on = this._hass.states[ids.led].state === "on";
        this._hass.callService("switch", on ? "turn_off" : "turn_on", {
          entity_id: ids.led,
        });
      };
    }

    const track = this.shadowRoot.getElementById("qty");
    if (track && ids.qty) {
      const min = Number(track.dataset.min), max = Number(track.dataset.max);
      const apply = (ev) => {
        const r = track.getBoundingClientRect();
        const x = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
        const frac = Math.max(0, Math.min(1, x / r.width));
        const v = Math.round(min + frac * (max - min));
        const pct = ((v - min) / Math.max(1, max - min)) * 100;
        track.querySelector(".fill").style.width = pct + "%";
        track.querySelector(".grip").style.left = pct + "%";
        const lbl = this.shadowRoot.getElementById("qtyval");
        if (lbl) lbl.textContent = v;
        return v;
      };
      track.onpointerdown = (e) => { track.setPointerCapture(e.pointerId); this._drag = true; apply(e); };
      track.onpointermove = (e) => { if (this._drag) apply(e); };
      track.onpointerup = (e) => {
        if (!this._drag) return;
        this._drag = false;
        this._hass.callService("number", "set_value",
          { entity_id: ids.qty, value: apply(e) });
      };
    }
  }

  _tap() {
    if (this._config.tap_action === "none") return;
    if (this._config.tap_action === "more-info") {
      this.dispatchEvent(new CustomEvent("hass-more-info", {
        detail: { entityId: this._anchor }, bubbles: true, composed: true }));
      return;
    }
    if (this._dialog) return;
    const dlg = document.createElement("ha-dialog");
    dlg.setAttribute("hideactions", "");
    dlg.heading = this._config.name || "SmartFeed";
    dlg.style.setProperty("--dialog-content-padding", "0");
    dlg.style.setProperty("--mdc-dialog-min-width", "min(94vw, 420px)");
    const card = document.createElement("juwel-feeder-card");
    card.setConfig({ ...this._config, layout: "full", tap_action: "none" });
    card.hass = this._hass;
    dlg.appendChild(card);
    dlg.addEventListener("closed", () => {
      dlg.remove(); this._dialog = null; this._popupCard = null;
    });
    document.body.appendChild(dlg);
    this._dialog = dlg;
    this._popupCard = card;
    dlg.open = true;
  }
}

class JuwelFeederCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { design: "juwel", layout: "full", tap_action: "popup", ...config };
    this._render();
  }
  set hass(hass) { this._hass = hass; this._render(); }
  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        this._config = ev.detail.value;
        this.dispatchEvent(new CustomEvent("config-changed",
          { detail: { config: this._config } }));
      });
      this.appendChild(this._form);
    }
    const T = t(this._hass);
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = [
      { name: "plan_sensor", required: true,
        selector: { entity: { domain: "sensor", integration: "juwel_appcontrol" } } },
      { name: "name", selector: { text: {} } },
      { name: "layout", selector: { select: { mode: "dropdown", options: [
          { value: "full", label: T.oFull }, { value: "compact", label: T.oCompact }] } } },
      { name: "design", selector: { select: { mode: "dropdown", options: [
          { value: "juwel", label: T.oJuwel }, { value: "ha", label: T.oHa }] } } },
      { name: "tap_action", selector: { select: { mode: "dropdown", options: [
          { value: "popup", label: T.oPopup }, { value: "more-info", label: T.oMore },
          { value: "none", label: T.oNone }] } } },
    ];
    this._form.computeLabel = (s) => ({
      plan_sensor: T.fFeeder, name: T.fName, layout: T.fLayout,
      design: T.fDesign, tap_action: T.fTap,
    }[s.name] || s.name);
  }
}

if (!customElements.get("juwel-feeder-card")) {
  customElements.define("juwel-feeder-card", JuwelFeederCard);
}
if (!customElements.get("juwel-feeder-card-editor")) {
  customElements.define("juwel-feeder-card-editor", JuwelFeederCardEditor);
}
if (!window.customCards.some((c) => c.type === "juwel-feeder-card"))
  window.customCards.push({
    type: "juwel-feeder-card",
    name: "Juwel SmartFeed",
    description: "Aquarium feeder: plan, feed now, quantity and chamber status",
    preview: true,
    documentationURL: "https://github.com/Melle79/juwel-appcontrol",
  });

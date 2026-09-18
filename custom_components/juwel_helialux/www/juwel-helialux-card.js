/*
 * Juwel HeliaLux Card  v1.3.0
 * Lovelace-Karte für die Integration "juwel_helialux".
 *
 * Optionen (alle im UI-Editor):
 *   design : "juwel" (MyJUWEL-Look) | "ha" (globales Home-Assistant-Theme)
 *   layout : "full"  (Kurve, Profil, Schalter, Regler) | "compact" (eine Zeile)
 */

const CH = [
  { key: "white", label: "W", name: "Weiß", color: "#ffffff" },
  { key: "red", label: "R", name: "Rot", color: "#e2574c" },
  { key: "green", label: "G", name: "Grün", color: "#3fbf6f" },
  { key: "blue", label: "B", name: "Blau", color: "#3d7fe3" },
];

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
      throw new Error("Bitte eine Licht-Entität der Juwel-Integration angeben.");
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

    this._ids.auto = c.auto_switch || siblings.find((e) => e.startsWith("switch."));
    this._ids.preset = c.preset_sensor || siblings.find((e) => e.startsWith("sensor."));

    CH.forEach((ch) => {
      this._ids[ch.key] =
        c[ch.key] ||
        siblings.find((e) => e.startsWith("number.") && fname(e).endsWith(ch.name));
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

    const body = this.shadowRoot.getElementById("body");
    const light = this._st(this._ids.light);
    if (!light) {
      body.innerHTML = `<div class="err">Entität <code>${this._lightId}</code> nicht gefunden.</div>`;
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
          <div class="status">Status:
            <span class="${online ? "ok" : "bad"}">${online ? "Online" : "Offline"}</span>
          </div>
        </div>
      </div>
      ${chart}
      <div class="prow">
        <div class="dot" style="background:${attrs.preset_color || "#b5d4e3"}"></div>
        <div class="plabel">Profil: ${preset ? preset.state : "–"}</div>
      </div>
      <div class="toggle-row">
        <div class="sw ${isAuto ? "" : "on"}" id="manual"><div class="knob"></div></div>
        <div class="toggle-label">Manueller Modus</div>
      </div>
      <div class="sliders ${isAuto ? "disabled" : ""}">
        ${CH.map((ch) => this._sliderHtml(ch)).join("")}
      </div>
      ${isAuto ? `<div class="hint">Im Automatikmodus sind die Regler gesperrt – Schalter oben umlegen.</div>` : ""}`;

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
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = [
      {
        name: "light",
        required: true,
        selector: { entity: { domain: "light", integration: "juwel_helialux" } },
      },
      { name: "name", selector: { text: {} } },
      {
        name: "layout",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "full", label: "Vollständig (Kurve, Profil, Regler)" },
              { value: "compact", label: "Kompakt (eine Zeile)" },
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
              { value: "juwel", label: "MyJUWEL-Look (dunkelblau)" },
              { value: "ha", label: "Home-Assistant-Theme übernehmen" },
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
              { value: "popup", label: "Große Karte als Popup öffnen" },
              { value: "more-info", label: "Detailansicht (more-info)" },
              { value: "hash", label: "Bubble-Card-Popup per Hash öffnen" },
              { value: "none", label: "Nichts tun" },
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
        light: "Licht-Entität (Juwel HeliaLux)",
        name: "Überschrift (optional)",
        layout: "Darstellung",
        design: "Design",
        show_chart: "Tageskurve anzeigen",
        tap_action: "Beim Antippen",
        popup_hash: "Hash des Bubble-Card-Popups (z. B. #aquarium)",
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
  description: "Aquarienlicht: Tageskurve, Profil und W/R/G/B – vollständig oder kompakt",
  preview: true,
  documentationURL: "https://github.com/Melle79/juwel-helialux",
});

console.info("%c JUWEL-HELIALUX-CARD %c v1.3.0 ", "background:#0b2239;color:#fff", "background:#2b6cb0;color:#fff");

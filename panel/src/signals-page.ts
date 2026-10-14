// Live signals: everything the radios hear, newest first, with what it
// decoded to and which command it matched, plus each radio's recent counts.
// The subscription runs only while this page is shown.

import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { errorMessage } from "./api";
import { heardTitle, radioLabel, statsLine } from "./format";
import { shared } from "./styles";
import type { ClickerRadio, Hass, Heard, RadioStats, ReceptionsUpdate } from "./types";

const KEEP = 200;

@customElement("clicker-signals-page")
export class ClickerSignalsPage extends LitElement {
  @property({ attribute: false }) hass!: Hass;
  @property({ attribute: false }) radios: ClickerRadio[] = [];

  @state() private _heard: Heard[] = [];
  @state() private _stats: Record<string, RadioStats> = {};
  @state() private _window = 600;
  @state() private _radio = "";
  @state() private _decodedOnly = false;
  @state() private _error?: string;

  private _unsubscribe?: Promise<() => Promise<void>>;

  connectedCallback(): void {
    super.connectedCallback();
    this._unsubscribe = this.hass.connection.subscribeMessage<ReceptionsUpdate>(
      (update) => {
        this._heard = [...update.heard].reverse().concat(this._heard).slice(0, KEEP);
        this._stats = update.stats;
        this._window = update.window_s;
      },
      { type: "clicker/receptions/subscribe" },
    );
    this._unsubscribe.catch((err) => (this._error = errorMessage(err)));
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._unsubscribe?.then((unsubscribe) => unsubscribe()).catch(() => undefined);
    this._unsubscribe = undefined;
    this._heard = [];
  }

  render() {
    if (this._error) return html`<p class="error">${this._error}</p>`;
    const radios = new Map(this.radios.map((r) => [r.id, r]));
    const shown = this._heard.filter(
      (h) => (!this._radio || h.radio_id === this._radio) && (!this._decodedOnly || h.bits),
    );
    return html`
      <div class="radios">
        ${this.radios
          .filter((r) => r.can_receive)
          .map(
            (r) => html`<div class="card radio-stats">
              <div class="name">${radioLabel(r.name, r.frequency_hz)}</div>
              <div class="meta">
                ${statsLine(this._stats[r.id])} in the last ${Math.round(this._window / 60)} minutes
              </div>
            </div>`,
          )}
      </div>
      <div class="filters">
        <select @change=${(e: Event) => (this._radio = (e.target as HTMLSelectElement).value)}>
          <option value="">All radios</option>
          ${this.radios.map((r) => html`<option value=${r.id}>${radioLabel(r.name, r.frequency_hz)}</option>`)}
        </select>
        <label class="check"
          ><input
            type="checkbox"
            .checked=${this._decodedOnly}
            @change=${(e: Event) => (this._decodedOnly = (e.target as HTMLInputElement).checked)}
          />Hide undecoded</label
        >
        <span class="spacer"></span>
        <span class="live"><span class="dot"></span>Live</span>
      </div>
      <div class="card list">
        ${shown.length
          ? shown.map((h) => this._renderHeard(h, radios.get(h.radio_id)))
          : html`<div class="meta empty">
              Nothing yet. Press a button on any remote near a radio.
            </div>`}
      </div>
    `;
  }

  private _renderHeard(heard: Heard, radio: ClickerRadio | undefined) {
    const time = new Date(heard.at * 1000).toLocaleTimeString(this.hass.language);
    return html`
      <div class="heard ${heard.bits ? "" : "undecoded"}">
        <span class="time">${time}</span>
        <div class="main">
          <div class="code">${heardTitle(heard)}</div>
          <div class="meta">
            ${radio ? radioLabel(radio.name, radio.frequency_hz) : "Unknown radio"}
            ${heard.bits ? html` · ${heard.encoding}` : nothing}
          </div>
        </div>
        ${heard.matches.length
          ? html`<span class="chip match">${heard.matches.join(", ")}</span>`
          : html`<span class="chip">${heard.bits ? "No match" : "Noise?"}</span>`}
      </div>
    `;
  }

  static styles = [
    shared,
    css`
      .radios {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 12px;
      }
      .radio-stats .name {
        font-weight: 500;
      }
      .filters {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 14px 0 8px;
        flex-wrap: wrap;
      }
      label.check {
        flex-direction: row;
        align-items: center;
        gap: 6px;
        font-size: 14px;
        color: var(--primary-text-color);
      }
      .spacer {
        flex: 1;
      }
      .live {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--secondary-text-color);
      }
      .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--success-color);
        animation: pulse 1.6s ease-in-out infinite;
      }
      @keyframes pulse {
        50% {
          opacity: 0.25;
        }
      }
      .list {
        padding: 4px 16px;
      }
      .heard {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0;
        border-top: 1px solid var(--divider-color);
      }
      .heard:first-child {
        border-top: none;
      }
      .heard.undecoded .code {
        color: var(--secondary-text-color);
      }
      .time {
        font-size: 13px;
        color: var(--secondary-text-color);
        font-variant-numeric: tabular-nums;
        min-width: 76px;
      }
      .main {
        flex: 1;
        min-width: 0;
      }
      .code {
        font-family: var(--code-font-family, monospace);
        font-size: 14px;
      }
      .chip.match {
        color: var(--success-color);
        border-color: var(--success-color);
      }
      .empty {
        padding: 16px 0;
      }
      .error {
        color: var(--error-color);
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "clicker-signals-page": ClickerSignalsPage;
  }
}

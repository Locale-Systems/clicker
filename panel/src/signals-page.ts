// Live signals: everything the radios hear, newest first, with what it
// decoded to and which command it matched, plus each radio's recent counts
// and the unknown sources heard more than once, which can be ignored (hidden
// here). The subscription runs only while this page is shown.

import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";

import { errorMessage, ignoreSource, unignoreSource } from "./api";
import { define } from "./define";
import { heardTitle, mhz, radioLabel, sourceRhythm, statsLine } from "./format";
import { shared } from "./styles";
import type {
  ClickerRadio,
  Hass,
  Heard,
  IgnoredSource,
  RadioStats,
  ReceptionsUpdate,
  Source,
} from "./types";

const KEEP = 200;

@define("clicker-signals-page")
export class ClickerSignalsPage extends LitElement {
  @property({ attribute: false }) hass!: Hass;
  @property({ attribute: false }) radios: ClickerRadio[] = [];
  @property({ attribute: false }) ignored: IgnoredSource[] = [];

  @state() private _heard: Heard[] = [];
  @state() private _stats: Record<string, RadioStats> = {};
  @state() private _window = 600;
  @state() private _radio = "";
  @state() private _decodedOnly = false;
  @state() private _showIgnored = false;
  @state() private _sources: Source[] = [];
  @state() private _naming?: { id: string; name: string };
  @state() private _ignoredOpen = false;
  @state() private _error?: string;

  private _unsubscribe?: Promise<() => Promise<void>>;

  connectedCallback(): void {
    super.connectedCallback();
    this._unsubscribe = this.hass.connection.subscribeMessage<ReceptionsUpdate>(
      (update) => {
        this._heard = [...update.heard].reverse().concat(this._heard).slice(0, KEEP);
        this._stats = update.stats;
        this._window = update.window_s;
        this._sources = update.sources;
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

  private _toast(message: string): void {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }),
    );
  }

  private async _ignore(source: Source, name: string): Promise<void> {
    try {
      await ignoreSource(this.hass, source.id, name.trim());
      this._naming = undefined;
      this._toast(`Ignoring ${name.trim() || source.label}`);
    } catch (err) {
      this._toast(errorMessage(err));
    }
  }

  private async _unignore(entry: IgnoredSource): Promise<void> {
    try {
      await unignoreSource(this.hass, entry.id);
    } catch (err) {
      this._toast(errorMessage(err));
    }
  }

  render() {
    if (this._error) return html`<p class="error">${this._error}</p>`;
    const radios = new Map(this.radios.map((r) => [r.id, r]));
    const sources = new Map(this._sources.map((s) => [s.id, s]));
    const sourceOf = (h: Heard) => (h.source_id ? sources.get(h.source_id) : undefined);
    const shown = this._heard.filter(
      (h) =>
        (!this._radio || h.radio_id === this._radio) &&
        (!this._decodedOnly || h.bits) &&
        (this._showIgnored || !sourceOf(h)?.ignored_id),
    );
    const active = this._sources.filter(
      (s) => !s.ignored_id && (!this._radio || s.radio_id === this._radio),
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
      ${active.length ? this._renderSources(active, radios) : nothing}
      ${this.ignored.length ? this._renderIgnored() : nothing}
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
        ${this.ignored.length
          ? html`<label class="check"
              ><input
                type="checkbox"
                .checked=${this._showIgnored}
                @change=${(e: Event) => (this._showIgnored = (e.target as HTMLInputElement).checked)}
              />Show ignored</label
            >`
          : nothing}
        <span class="spacer"></span>
        <span class="live"><span class="dot"></span>Live</span>
      </div>
      <div class="card list">
        ${shown.length
          ? shown.map((h) => this._renderHeard(h, radios.get(h.radio_id), sourceOf(h)))
          : html`<div class="meta empty">
              Nothing yet. Press a button on any remote near a radio.
            </div>`}
      </div>
    `;
  }

  private _renderSources(sources: Source[], radios: Map<string, ClickerRadio>) {
    return html`<div class="card sources">
      <div class="card-title">Unknown sources</div>
      <div class="meta intro">
        Transmitters heard more than once that match no command: sensors, doorbells, other remotes.
        Ignore the ones you don't need to see.
      </div>
      ${sources.map((source) => this._renderSource(source, radios.get(source.radio_id)))}
    </div>`;
  }

  private _renderSource(source: Source, radio: ClickerRadio | undefined) {
    const last = new Date(source.last_seen * 1000).toLocaleTimeString(this.hass.language);
    const naming = this._naming?.id === source.id ? this._naming : undefined;
    const setName = (e: Event) =>
      (this._naming = { id: source.id, name: (e.target as HTMLInputElement).value });
    return html`<div class="source">
      <div class="source-head">
        <span class="source-label">${source.label}</span>
        <span class="meta">${sourceRhythm(source)} · last ${last}</span>
        <span class="spacer"></span>
        ${naming
          ? nothing
          : html`<button @click=${() => (this._naming = { id: source.id, name: "" })}>Ignore…</button>`}
      </div>
      <div class="code">${source.description}</div>
      ${this.radios.length > 1 && radio
        ? html`<div class="meta">${radioLabel(radio.name, radio.frequency_hz)}</div>`
        : nothing}
      ${naming
        ? html`<div class="naming">
            <input
              placeholder="Name it (optional), e.g. Neighbour's weather sensor"
              .value=${naming.name}
              @input=${setName}
              @keydown=${(e: KeyboardEvent) => e.key === "Enter" && this._ignore(source, naming.name)}
            />
            <button @click=${() => (this._naming = undefined)}>Cancel</button>
            <button class="primary" @click=${() => this._ignore(source, naming.name)}>Ignore</button>
          </div>`
        : nothing}
    </div>`;
  }

  private _renderIgnored() {
    return html`<div class="card ignored">
      <button class="link" @click=${() => (this._ignoredOpen = !this._ignoredOpen)}>
        <ha-icon .icon=${this._ignoredOpen ? "mdi:chevron-down" : "mdi:chevron-right"}></ha-icon>
        Ignored sources (${this.ignored.length})
      </button>
      ${this._ignoredOpen
        ? this.ignored.map(
            (entry) => html`<div class="source">
              <div class="source-head">
                <span class="source-label">${entry.name || "Unnamed source"}</span>
                <span class="meta">${mhz(entry.frequency_hz)}</span>
                <span class="spacer"></span>
                <button @click=${() => this._unignore(entry)}>Show again</button>
              </div>
              <div class="code">${entry.description}</div>
            </div>`,
          )
        : nothing}
    </div>`;
  }

  private _renderHeard(heard: Heard, radio: ClickerRadio | undefined, source?: Source) {
    const time = new Date(heard.at * 1000).toLocaleTimeString(this.hass.language);
    return html`
      <div class="heard ${heard.bits ? "" : "undecoded"}">
        <span class="time">${time}</span>
        <div class="main">
          <div class="code">${heardTitle(heard)}</div>
          ${this.radios.length > 1 || heard.bits
            ? html`<div class="meta">
                ${this.radios.length > 1
                  ? radio
                    ? radioLabel(radio.name, radio.frequency_hz)
                    : "Unknown radio"
                  : nothing}
                ${this.radios.length > 1 && heard.bits ? " · " : nothing}${heard.bits ? heard.encoding : nothing}
              </div>`
            : nothing}
        </div>
        ${heard.matches.length
          ? html`<span class="chip match">${heard.matches.join(", ")}</span>`
          : source
            ? html`<span class="chip source ${source.ignored_id ? "ignored" : ""}">${source.label}</span>`
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
        min-width: 64px;
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
      .chip.source {
        color: var(--primary-color);
        border-color: var(--primary-color);
      }
      .chip.source.ignored {
        color: var(--secondary-text-color);
        border-color: var(--divider-color);
      }
      .sources,
      .ignored {
        margin-top: 12px;
      }
      .intro {
        margin-bottom: 4px;
      }
      .source {
        padding: 8px 0;
        border-top: 1px solid var(--divider-color);
      }
      .intro + .source,
      .link + .source {
        border-top: none;
      }
      .source-head {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
      }
      .source-label {
        font-weight: 500;
      }
      .naming {
        display: flex;
        gap: 8px;
        margin-top: 8px;
        flex-wrap: wrap;
      }
      .naming input {
        flex: 1;
        min-width: 200px;
      }
      button.link {
        display: flex;
        align-items: center;
        gap: 4px;
        background: none;
        border: none;
        padding: 0;
        font: inherit;
        font-weight: 500;
        color: var(--primary-text-color);
        cursor: pointer;
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

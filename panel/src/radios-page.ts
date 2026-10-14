// Radios: each ESPHome radio Clicker found, with its state, what it can do,
// how much it hears, advice, rename, and delete (only when no device uses it).

import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";

import { deleteRadio, errorMessage, renameRadio } from "./api";
import { define } from "./define";
import { count, mhz, radioHints } from "./format";
import { shared } from "./styles";
import type { ClickerData, ClickerRadio, Hass } from "./types";

@define("clicker-radios-page")
export class ClickerRadiosPage extends LitElement {
  @property({ attribute: false }) hass!: Hass;
  @property({ attribute: false }) data!: ClickerData;

  @state() private _renaming?: { id: string; name: string };
  @state() private _confirmDelete?: string;

  private _toast(message: string): void {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }),
    );
  }

  private async _rename(): Promise<void> {
    const draft = this._renaming!;
    try {
      await renameRadio(this.hass, draft.id, draft.name.trim());
      this._renaming = undefined;
      this._toast("Saved");
    } catch (err) {
      this._toast(errorMessage(err));
    }
  }

  private async _delete(radio: ClickerRadio): Promise<void> {
    try {
      await deleteRadio(this.hass, radio.id);
      this._confirmDelete = undefined;
      this._toast(`Deleted ${radio.name}`);
    } catch (err) {
      this._toast(errorMessage(err));
    }
  }

  render() {
    if (!this.data.radios.length) {
      return html`<div class="card meta">
        No radios yet. Clicker finds ESPHome nodes with an RF transmitter or receiver
        (<code>radio_frequency</code> with <code>ir_rf_proxy</code>) once they're added to Home
        Assistant.
      </div>`;
    }
    return html`<div class="grid">${this.data.radios.map((r) => this._renderRadio(r))}</div>`;
  }

  private _renderRadio(radio: ClickerRadio) {
    const devices = this.data.devices.filter((d) => d.radio_id === radio.id);
    const renaming = this._renaming?.id === radio.id;
    const confirming = this._confirmDelete === radio.id;
    return html`
      <div class="card">
        ${renaming
          ? html`<div class="rename">
              <input
                .value=${this._renaming!.name}
                @input=${(e: Event) =>
                  (this._renaming = { id: radio.id, name: (e.target as HTMLInputElement).value })}
              />
              <button @click=${() => (this._renaming = undefined)}>Cancel</button>
              <button class="primary" ?disabled=${!this._renaming!.name.trim()} @click=${this._rename}>
                Save
              </button>
            </div>`
          : html`<div class="card-title">
              <span class="name">${radio.name}</span>
              <button
                class="icon"
                aria-label="Rename ${radio.name}"
                @click=${() => (this._renaming = { id: radio.id, name: radio.name })}
              >
                <ha-icon icon="mdi:pencil"></ha-icon>
              </button>
              ${devices.length
                ? nothing
                : html`<button
                    class="icon"
                    aria-label="Delete ${radio.name}"
                    @click=${() => (this._confirmDelete = radio.id)}
                  >
                    <ha-icon icon="mdi:delete-outline"></ha-icon>
                  </button>`}
            </div>`}
        <div class="chips">
          <span class="chip ${radio.online ? "ok" : "warning"}">${radio.online ? "Online" : "Offline"}</span>
          <span class="chip">${mhz(radio.frequency_hz)}</span>
          ${radio.can_send ? html`<span class="chip">Sends</span>` : nothing}
          ${radio.can_receive ? html`<span class="chip">Receives</span>` : nothing}
        </div>
        <div class="meta">
          ${radio.node ? html`On ${radio.node} · ` : nothing}
          ${devices.length
            ? `Used by ${devices.map((d) => d.name).join(", ")}`
            : `${count(0, "device")}`}
        </div>
        ${radioHints(radio, devices.length).map((hint) => html`<div class="hint">${hint}</div>`)}
        ${confirming
          ? html`<div class="confirm">
              Delete ${radio.name}?
              ${radio.online ? "It's online, so Clicker will find it again." : ""}
              <div class="actions">
                <span class="spacer"></span>
                <button @click=${() => (this._confirmDelete = undefined)}>Cancel</button>
                <button class="danger" @click=${() => this._delete(radio)}>Delete</button>
              </div>
            </div>`
          : nothing}
      </div>
    `;
  }

  static styles = [
    shared,
    css`
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 12px;
      }
      .name {
        flex: 1;
      }
      .chips {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        margin-bottom: 6px;
      }
      .chip.ok {
        color: var(--success-color);
        border-color: var(--success-color);
      }
      .hint {
        font-size: 13px;
        margin-top: 6px;
      }
      .rename {
        display: flex;
        gap: 8px;
        margin-bottom: 8px;
      }
      .rename input {
        flex: 1;
      }
      .confirm {
        margin-top: 8px;
        font-size: 14px;
      }
      .actions {
        display: flex;
        gap: 8px;
        margin-top: 8px;
      }
      .spacer {
        flex: 1;
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "clicker-radios-page": ClickerRadiosPage;
  }
}

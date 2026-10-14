// Devices: every device by area, with its radio, commands and entities;
// adding a device; importing from RF Device Manager.

import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { createDevice, errorMessage, importRun, importStatus } from "./api";
import {
  PLATFORM_ICONS,
  count,
  entitySummary,
  groupByArea,
  importSummary,
  radioLabel,
} from "./format";
import { shared } from "./styles";
import type { ClickerData, ClickerDevice, ClickerRadio, Hass } from "./types";

interface NewDevice {
  name: string;
  radio: string;
  area: string;
}

@customElement("clicker-devices-page")
export class ClickerDevicesPage extends LitElement {
  @property({ attribute: false }) hass!: Hass;
  @property({ attribute: false }) data!: ClickerData;

  @state() private _new?: NewDevice;
  @state() private _canImport = false;
  @state() private _import?: "confirm" | "running" | { notes: string[]; problems: string[] };

  connectedCallback(): void {
    super.connectedCallback();
    importStatus(this.hass)
      .then((status) => (this._canImport = status.available))
      .catch(() => undefined);
  }

  private _navigate(path: string): void {
    this.dispatchEvent(new CustomEvent("navigate", { detail: { path } }));
  }

  private _toast(message: string): void {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }),
    );
  }

  private _startNew(): void {
    const radio = this.data.radios.find((r) => r.online && r.can_send) ?? this.data.radios[0];
    this._new = { name: "", radio: radio?.id ?? "", area: "" };
  }

  private _nameTaken(name: string): boolean {
    return this.data.devices.some((d) => d.name.toLowerCase() === name.trim().toLowerCase());
  }

  private async _create(): Promise<void> {
    const draft = this._new!;
    try {
      const device = await createDevice(this.hass, {
        name: draft.name.trim(),
        radio_id: draft.radio,
        area_id: draft.area || null,
      });
      this._new = undefined;
      this._navigate(`/device/${device.id}/learn`);
    } catch (err) {
      this._toast(errorMessage(err));
    }
  }

  private async _runImport(): Promise<void> {
    this._import = "running";
    try {
      this._import = await importRun(this.hass);
    } catch (err) {
      this._import = undefined;
      this._toast(errorMessage(err));
    }
  }

  render() {
    const { devices, radios, problems } = this.data;
    return html`
      <div class="actions">
        ${this._new ? nothing : html`<button class="primary" ?disabled=${!radios.length} @click=${this._startNew}>
          <ha-icon icon="mdi:plus"></ha-icon> New device
        </button>`}
        ${this._canImport && !this._import
          ? html`<button @click=${() => (this._import = "confirm")}>Import from RF Device Manager</button>`
          : nothing}
      </div>
      ${this._new ? this._renderNew(this._new) : nothing} ${this._renderImport()}
      ${problems.length
        ? html`<div class="problems">${problems.map((p) => html`<div>${p}</div>`)}</div>`
        : nothing}
      ${devices.length ? this._renderAreas() : this._new ? nothing : this._renderEmpty(radios)}
    `;
  }

  private _renderEmpty(radios: ClickerRadio[]) {
    return html`<div class="empty">
      <h2>Set up your first remote</h2>
      <p>
        Add a device, then press its remote's buttons to teach Clicker each one. Clicker turns
        them into fans, lights, switches and buttons.
      </p>
      <p class="meta">
        ${radios.length
          ? `Radios ready: ${radios.map((r) => radioLabel(r.name, r.frequency_hz)).join(", ")}.`
          : "No radios yet. Clicker finds ESPHome radios with an RF transmitter or receiver."}
      </p>
    </div>`;
  }

  private _renderNew(draft: NewDevice) {
    const set = (patch: Partial<NewDevice>) => (this._new = { ...draft, ...patch });
    const taken = this._nameTaken(draft.name);
    const areas = Object.values(this.hass.areas).sort((a, b) => a.name.localeCompare(b.name));
    return html`<div class="card new">
      <div class="card-title">New device</div>
      <div class="form">
        <label
          >Name
          <input
            placeholder="Bedroom fan"
            .value=${draft.name}
            @input=${(e: Event) => set({ name: (e.target as HTMLInputElement).value })}
          />
          ${taken ? html`<span class="hint error">You already have a device with that name</span>` : nothing}
        </label>
        <label
          >Radio
          <select @change=${(e: Event) => set({ radio: (e.target as HTMLSelectElement).value })}>
            ${this.data.radios.map(
              (r) => html`<option value=${r.id} ?selected=${r.id === draft.radio}>
                ${radioLabel(r.name, r.frequency_hz)}${r.online ? "" : " (offline)"}
              </option>`,
            )}
          </select>
          <span class="hint">The radio on your remote's frequency.</span>
        </label>
        <label
          >Area
          <select @change=${(e: Event) => set({ area: (e.target as HTMLSelectElement).value })}>
            <option value="">No area</option>
            ${areas.map((a) => html`<option value=${a.area_id}>${a.name}</option>`)}
          </select>
        </label>
      </div>
      <div class="row-actions">
        <span class="spacer"></span>
        <button @click=${() => (this._new = undefined)}>Cancel</button>
        <button
          class="primary"
          ?disabled=${!draft.name.trim() || taken || !draft.radio}
          @click=${this._create}
        >
          Add and learn buttons
        </button>
      </div>
    </div>`;
  }

  private _renderImport() {
    const state = this._import;
    if (!state) return nothing;
    if (state === "confirm" || state === "running") {
      return html`<div class="card">
        <div class="card-title">Import from RF Device Manager</div>
        <p class="text">
          Copies RF Device Manager's devices and codes into Clicker, re-encoding each code and
          building entities from them. Devices Clicker already has (by name) are skipped, so it's
          safe to run again. RF Device Manager itself isn't changed.
        </p>
        <div class="row-actions">
          <span class="spacer"></span>
          <button ?disabled=${state === "running"} @click=${() => (this._import = undefined)}>Cancel</button>
          <button class="primary" ?disabled=${state === "running"} @click=${this._runImport}>
            ${state === "running" ? "Importing…" : "Import"}
          </button>
        </div>
      </div>`;
    }
    return html`<div class="card">
      <div class="card-title">
        Import finished <span class="spacer"></span>
        <button class="icon" aria-label="Close" @click=${() => (this._import = undefined)}>
          <ha-icon icon="mdi:close"></ha-icon>
        </button>
      </div>
      ${state.problems.length
        ? html`<div class="problems">${state.problems.map((p) => html`<div>${p}</div>`)}</div>`
        : nothing}
      <div class="text">${importSummary(state.notes)}</div>
      <details>
        <summary class="meta">Details</summary>
        <ul class="notes">
          ${state.notes.map((note) => html`<li>${note}</li>`)}
        </ul>
      </details>
    </div>`;
  }

  private _renderAreas() {
    const radioById = new Map(this.data.radios.map((r) => [r.id, r]));
    return groupByArea(this.data.devices, this.hass.areas).map(
      (group) => html`
        <h2 class="area">${group.name}</h2>
        <div class="grid">
          ${group.devices.map((d) => this._renderDevice(d, radioById.get(d.radio_id)))}
        </div>
      `,
    );
  }

  private _renderDevice(device: ClickerDevice, radio: ClickerRadio | undefined) {
    const entities = device.bindings.flatMap((b) =>
      (b.entity_ids.length ? b.entity_ids : [undefined]).map((entityId) => ({ binding: b, entityId })),
    );
    const open = () => this._navigate(`/device/${device.id}`);
    return html`
      <div
        class="card clickable"
        role="button"
        tabindex="0"
        @click=${open}
        @keydown=${(e: KeyboardEvent) => e.key === "Enter" && open()}
      >
        <div class="card-head">
          <span class="name">${device.name}</span>
          ${radio?.online
            ? nothing
            : html`<span class="chip warning">${radio ? "Radio offline" : "No radio"}</span>`}
        </div>
        <div class="meta">
          ${radioLabel(radio?.name, device.frequency_hz)} · ${count(device.commands.length, "command")}
        </div>
        ${entities.length
          ? html`<div class="entities">
              ${entities.map(({ binding, entityId }) => {
                const state = entityId ? this.hass.states[entityId] : undefined;
                const name = (state?.attributes.friendly_name as string | undefined) ?? binding.name;
                return html`<div class="entity">
                  <ha-icon .icon=${PLATFORM_ICONS[binding.platform] ?? "mdi:remote"}></ha-icon>
                  <span class="entity-name">${name}</span>
                  <span class="meta">${entitySummary(state)}</span>
                </div>`;
              })}
            </div>`
          : html`<div class="meta">${device.commands.length ? "No entities yet" : "No commands yet"}</div>`}
      </div>
    `;
  }

  static styles = [
    shared,
    css`
      .actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin: 8px 0 12px;
      }
      .actions button {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }
      .actions ha-icon {
        --mdc-icon-size: 18px;
      }
      .card {
        margin-bottom: 12px;
      }
      .grid .card {
        margin-bottom: 0;
      }
      .form {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 10px;
      }
      .row-actions {
        display: flex;
        gap: 8px;
        margin-top: 12px;
      }
      .spacer {
        flex: 1;
      }
      .hint {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .hint.error {
        color: var(--error-color);
      }
      .text {
        font-size: 14px;
        margin: 0;
      }
      details {
        margin-top: 8px;
      }
      summary {
        cursor: pointer;
      }
      .notes {
        margin: 6px 0 0;
        padding-left: 20px;
        font-size: 13px;
        color: var(--secondary-text-color);
      }
      .area {
        font-size: 16px;
        font-weight: 500;
        color: var(--secondary-text-color);
        margin: 20px 4px 8px;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 12px;
      }
      .clickable {
        cursor: pointer;
      }
      .clickable:hover,
      .clickable:focus-visible {
        border-color: var(--primary-color);
        outline: none;
      }
      .card-head {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .name {
        font-size: 16px;
        font-weight: 500;
        flex: 1;
      }
      .entities {
        margin-top: 10px;
        border-top: 1px solid var(--divider-color);
        padding-top: 8px;
      }
      .entity {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 4px 0;
        font-size: 14px;
      }
      .entity ha-icon {
        color: var(--state-icon-color, var(--secondary-text-color));
      }
      .entity-name {
        flex: 1;
      }
      .problems {
        margin: 12px 0;
        padding: 10px 14px;
        border-radius: 8px;
        border: 1px solid var(--warning-color);
        font-size: 14px;
      }
      .empty {
        text-align: center;
        padding: 40px 16px;
      }
      .empty h2 {
        font-weight: 400;
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "clicker-devices-page": ClickerDevicesPage;
  }
}

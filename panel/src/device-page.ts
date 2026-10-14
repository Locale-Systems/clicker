// One device: its settings, its commands (test, edit, delete) and its entities.
// Changes go through the websocket API; the panel's data subscription brings
// the updated device back, so this view keeps no copy of its own.

import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import {
  deleteBinding,
  deleteCommand,
  errorMessage,
  sendCommand,
  updateCommand,
  updateDevice,
} from "./api";
import "./entity-editor";
import "./learn-drawer";
import {
  KIND_HINTS,
  KIND_LABELS,
  commandUsage,
  describeUsage,
  entitySummary,
  radioLabel,
  radiosFor,
  type Usage,
} from "./format";
import { shared } from "./styles";
import { detectTemplate } from "./templates";
import type { ClickerBinding, ClickerCommand, ClickerDevice, ClickerRadio, Hass } from "./types";

const PLATFORM_ICONS: Record<string, string> = {
  fan: "mdi:fan",
  light: "mdi:lightbulb",
  switch: "mdi:toggle-switch-variant",
  button: "mdi:gesture-tap-button",
};

interface CommandDraft {
  id: string;
  name: string;
  kind: string;
  frames: number;
}

@customElement("clicker-device-page")
export class ClickerDevicePage extends LitElement {
  @property({ attribute: false }) hass!: Hass;
  @property({ attribute: false }) device!: ClickerDevice;
  @property({ attribute: false }) radios: ClickerRadio[] = [];

  @state() private _editing?: CommandDraft;
  @state() private _confirmDelete?: string; // command id
  @state() private _sending = new Set<string>();
  @state() private _settings?: { name: string; area: string; radio: string };
  @state() private _learning = false;
  @state() private _editingBinding?: string; // binding id, or "new"
  @state() private _confirmRemove?: string; // binding id

  private _toast(message: string): void {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }),
    );
  }

  private async _call(action: () => Promise<unknown>, done?: string): Promise<boolean> {
    try {
      await action();
      if (done) this._toast(done);
      return true;
    } catch (err) {
      this._toast(errorMessage(err));
      return false;
    }
  }

  // --- Settings --------------------------------------------------------------

  private _currentSettings() {
    return (
      this._settings ?? {
        name: this.device.name,
        area: this.device.area_id ?? "",
        radio: this.device.radio_id,
      }
    );
  }

  private _settingsChanged(): boolean {
    const s = this._currentSettings();
    return (
      s.name.trim() !== this.device.name ||
      s.area !== (this.device.area_id ?? "") ||
      s.radio !== this.device.radio_id
    );
  }

  private async _saveSettings(): Promise<void> {
    const s = this._currentSettings();
    const changes: { name?: string; area_id?: string | null; radio_id?: string } = {};
    if (s.name.trim() !== this.device.name) changes.name = s.name.trim();
    if (s.area !== (this.device.area_id ?? "")) changes.area_id = s.area || null;
    if (s.radio !== this.device.radio_id) changes.radio_id = s.radio;
    if (await this._call(() => updateDevice(this.hass, this.device.id, changes), "Saved")) {
      this._settings = undefined;
    }
  }

  private _renderSettings() {
    const s = this._currentSettings();
    const set = (patch: Partial<typeof s>) => (this._settings = { ...s, ...patch });
    const areas = Object.values(this.hass.areas).sort((a, b) => a.name.localeCompare(b.name));
    const radios = radiosFor(this.device, this.radios);
    return html`
      <div class="card">
        <div class="card-title">Device</div>
        <div class="settings">
          <label
            >Name
            <input
              .value=${s.name}
              @input=${(e: Event) => set({ name: (e.target as HTMLInputElement).value })}
          /></label>
          <label
            >Area
            <select @change=${(e: Event) => set({ area: (e.target as HTMLSelectElement).value })}>
              <option value="" ?selected=${!s.area}>No area</option>
              ${areas.map(
                (a) => html`<option value=${a.area_id} ?selected=${a.area_id === s.area}>
                  ${a.name}
                </option>`,
              )}
            </select></label
          >
          <label
            >Radio
            <select @change=${(e: Event) => set({ radio: (e.target as HTMLSelectElement).value })}>
              ${radios.map(
                (r) => html`<option value=${r.id} ?selected=${r.id === s.radio}>
                  ${radioLabel(r.name, r.frequency_hz)}${r.online ? "" : " (offline)"}
                </option>`,
              )}
            </select></label
          >
        </div>
        <div class="actions">
          ${this.device.ha_device_id
            ? html`<a class="link" href="/config/devices/device/${this.device.ha_device_id}"
                >Open in Home Assistant</a
              >`
            : nothing}
          <span class="spacer"></span>
          ${this._settingsChanged()
            ? html`<button @click=${() => (this._settings = undefined)}>Cancel</button>
                <button class="primary" ?disabled=${!s.name.trim()} @click=${this._saveSettings}>
                  Save
                </button>`
            : nothing}
        </div>
      </div>
    `;
  }

  // --- Commands --------------------------------------------------------------

  private async _test(command: ClickerCommand): Promise<void> {
    this._sending = new Set([...this._sending, command.id]);
    await this._call(() => sendCommand(this.hass, this.device.id, command.id), `Sent ${command.name}`);
    this._sending = new Set([...this._sending].filter((id) => id !== command.id));
  }

  private async _saveCommand(): Promise<void> {
    const draft = this._editing!;
    const command = this.device.commands.find((c) => c.id === draft.id);
    if (!command) return;
    const changes: { name?: string; kind?: string; frames_on_air?: number } = {};
    if (draft.name.trim() !== command.name) changes.name = draft.name.trim();
    if (draft.kind !== command.kind) changes.kind = draft.kind;
    if (draft.frames !== command.frames_on_air) changes.frames_on_air = draft.frames;
    if (!Object.keys(changes).length) {
      this._editing = undefined;
      return;
    }
    if (await this._call(() => updateCommand(this.hass, this.device.id, draft.id, changes), "Saved")) {
      this._editing = undefined;
    }
  }

  private async _delete(command: ClickerCommand): Promise<void> {
    if (await this._call(() => deleteCommand(this.hass, this.device.id, command.id), `Deleted ${command.name}`)) {
      this._confirmDelete = undefined;
    }
  }

  private _renderCommands() {
    const usage = commandUsage(this.device);
    return html`
      <div class="card">
        <div class="card-title">
          Commands <span class="meta">${this.device.commands.length}</span>
          <span class="spacer"></span>
          ${this._learning
            ? nothing
            : html`<button @click=${() => (this._learning = true)}>
                <ha-icon icon="mdi:plus"></ha-icon> Learn
              </button>`}
        </div>
        ${this.device.commands.length
          ? this.device.commands.map((c) => this._renderCommand(c, usage.get(c.id) ?? []))
          : html`<div class="meta">No commands yet. Press Learn, then press buttons on the remote.</div>`}
      </div>
    `;
  }

  private _renderCommand(command: ClickerCommand, usages: Usage[]) {
    if (this._editing?.id === command.id) return this._renderEditor(this._editing);
    const confirming = this._confirmDelete === command.id;
    const sending = this._sending.has(command.id);
    return html`
      <div class="row ${confirming ? "confirming" : ""}">
        <div class="row-main">
          <div class="row-name">${command.name}</div>
          <div class="meta">
            ${KIND_LABELS[command.kind]} ·
            ${command.encoded ? `${command.bits?.length ?? 0}-bit ${command.encoding}` : "raw"} ·
            ${command.frames_on_air === 1 ? "sent once" : `${command.frames_on_air} frames`}
            ${usages.length ? html` · used by ${describeUsage(usages)}` : nothing}
          </div>
          ${confirming
            ? html`<div class="confirm">
                ${usages.length
                  ? html`Delete ${command.name}? ${describeUsage(usages)} will lose it, and an
                    entity that can't work without it is removed.`
                  : html`Delete ${command.name}? You'd need to learn it again.`}
                <div class="actions">
                  <span class="spacer"></span>
                  <button @click=${() => (this._confirmDelete = undefined)}>Cancel</button>
                  <button class="danger" @click=${() => this._delete(command)}>Delete</button>
                </div>
              </div>`
            : nothing}
        </div>
        ${confirming
          ? nothing
          : html`<button ?disabled=${sending} @click=${() => this._test(command)}>
                ${sending ? "Sending…" : "Test"}
              </button>
              <button
                class="icon"
                aria-label="Edit ${command.name}"
                @click=${() =>
                  (this._editing = {
                    id: command.id,
                    name: command.name,
                    kind: command.kind,
                    frames: command.frames_on_air,
                  })}
              >
                <ha-icon icon="mdi:pencil"></ha-icon>
              </button>
              <button
                class="icon"
                aria-label="Delete ${command.name}"
                @click=${() => (this._confirmDelete = command.id)}
              >
                <ha-icon icon="mdi:delete-outline"></ha-icon>
              </button>`}
      </div>
    `;
  }

  private _renderEditor(draft: CommandDraft) {
    const set = (patch: Partial<CommandDraft>) => (this._editing = { ...draft, ...patch });
    const frames = Number.isInteger(draft.frames) && draft.frames >= 1 && draft.frames <= 64;
    return html`
      <div class="row editing">
        <div class="editor">
          <label
            >Name
            <input
              .value=${draft.name}
              @input=${(e: Event) => set({ name: (e.target as HTMLInputElement).value })}
          /></label>
          <label
            >Kind
            <select @change=${(e: Event) => set({ kind: (e.target as HTMLSelectElement).value })}>
              ${Object.entries(KIND_LABELS).map(
                ([kind, label]) => html`<option value=${kind} ?selected=${kind === draft.kind}>
                  ${label}
                </option>`,
              )}
            </select>
            <span class="hint">${KIND_HINTS[draft.kind]}</span></label
          >
          <label
            >Frames on air
            <input
              type="number"
              min="1"
              max="64"
              .value=${String(draft.frames)}
              @input=${(e: Event) => set({ frames: Number((e.target as HTMLInputElement).value) })}
            />
            <span class="hint ${frames ? "" : "error"}"
              >${frames ? "1 sends once; 8 is a short press" : "Enter 1 to 64"}</span
            ></label
          >
        </div>
        <div class="actions">
          <span class="spacer"></span>
          <button @click=${() => (this._editing = undefined)}>Cancel</button>
          <button class="primary" ?disabled=${!draft.name.trim() || !frames} @click=${this._saveCommand}>
            Save
          </button>
        </div>
      </div>
    `;
  }

  // --- Entities --------------------------------------------------------------

  private async _removeBinding(binding: ClickerBinding): Promise<void> {
    if (await this._call(() => deleteBinding(this.hass, this.device.id, binding.id), `Removed ${binding.name}`)) {
      this._confirmRemove = undefined;
    }
  }

  private _renderEntities() {
    const adding = this._editingBinding === "new";
    return html`
      <div class="card">
        <div class="card-title">
          Entities <span class="spacer"></span>
          ${this._editingBinding || !this.device.commands.length
            ? nothing
            : html`<button @click=${() => (this._editingBinding = "new")}>
                <ha-icon icon="mdi:plus"></ha-icon> Add
              </button>`}
        </div>
        ${adding
          ? html`<clicker-entity-editor
              .hass=${this.hass}
              .device=${this.device}
              @close=${() => (this._editingBinding = undefined)}
            ></clicker-entity-editor>`
          : nothing}
        ${this.device.bindings.length
          ? this.device.bindings.map((b) => this._renderBinding(b))
          : adding
            ? nothing
            : html`<div class="meta">
                ${this.device.commands.length
                  ? "No entities yet. Add one to control this device from Home Assistant."
                  : "Learn some commands first, then add entities built from them."}
              </div>`}
      </div>
    `;
  }

  private _renderBinding(binding: ClickerBinding) {
    if (this._editingBinding === binding.id) {
      return html`<div class="binding">
        <clicker-entity-editor
          .hass=${this.hass}
          .device=${this.device}
          .binding=${binding}
          @close=${() => (this._editingBinding = undefined)}
        ></clicker-entity-editor>
      </div>`;
    }
    const { template } = detectTemplate(binding);
    const confirming = this._confirmRemove === binding.id;
    const entityIds = binding.entity_ids.length ? binding.entity_ids : [undefined];
    return html`
      <div class="binding">
        <div class="entity">
          <ha-icon .icon=${PLATFORM_ICONS[binding.platform] ?? "mdi:remote"}></ha-icon>
          <div class="row-main">
            <div>${binding.name}</div>
            <div class="meta">${template.label}</div>
          </div>
          ${confirming
            ? nothing
            : html`<button
                  class="icon"
                  aria-label="Edit ${binding.name}"
                  @click=${() => (this._editingBinding = binding.id)}
                >
                  <ha-icon icon="mdi:pencil"></ha-icon>
                </button>
                <button
                  class="icon"
                  aria-label="Remove ${binding.name}"
                  @click=${() => (this._confirmRemove = binding.id)}
                >
                  <ha-icon icon="mdi:delete-outline"></ha-icon>
                </button>`}
        </div>
        ${entityIds.map((entityId) => {
          const st = entityId ? this.hass.states[entityId] : undefined;
          return html`<div class="entity-state-row meta">
            <span>${entityId ?? "Not created yet"}</span><span>${entitySummary(st)}</span>
          </div>`;
        })}
        ${confirming
          ? html`<div class="confirm">
              Remove the ${binding.name} ${binding.platform === "button" ? "buttons" : binding.platform}?
              ${binding.platform === "button" ? "Their" : "Its"} commands stay on the device.
              <div class="actions">
                <span class="spacer"></span>
                <button @click=${() => (this._confirmRemove = undefined)}>Cancel</button>
                <button class="danger" @click=${() => this._removeBinding(binding)}>Remove</button>
              </div>
            </div>`
          : nothing}
      </div>
    `;
  }

  render() {
    return html`
      <div class="layout">
        <div class="column">${this._renderCommands()}</div>
        <div class="column">
          ${this._learning
            ? html`<clicker-learn-drawer
                .hass=${this.hass}
                .device=${this.device}
                @close=${() => (this._learning = false)}
              ></clicker-learn-drawer>`
            : nothing}
          ${this._renderSettings()} ${this._renderEntities()}
        </div>
      </div>
    `;
  }

  static styles = [
    shared,
    css`
      .layout {
        display: grid;
        grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
        gap: 12px;
        align-items: start;
      }
      @media (max-width: 800px) {
        .layout {
          grid-template-columns: minmax(0, 1fr);
        }
      }
      .card-title button {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-weight: 400;
      }
      .card-title button ha-icon {
        --mdc-icon-size: 18px;
      }
      .column {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .settings {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .actions {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 10px;
      }
      .spacer {
        flex: 1;
      }
      .link {
        color: var(--primary-color);
        font-size: 14px;
        text-decoration: none;
      }
      .row {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 0;
        border-top: 1px solid var(--divider-color);
      }
      .row:first-of-type {
        border-top: none;
      }
      .row.editing {
        flex-direction: column;
        align-items: stretch;
      }
      .row-main {
        flex: 1;
        min-width: 0;
      }
      .row-name {
        font-size: 15px;
      }
      .confirm {
        margin-top: 6px;
        font-size: 14px;
      }
      .editor {
        display: grid;
        grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) minmax(0, 1fr);
        gap: 10px;
      }
      @media (max-width: 500px) {
        .editor {
          grid-template-columns: minmax(0, 1fr);
        }
      }
      .hint {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .hint.error {
        color: var(--error-color);
      }
      .entity {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 0;
      }
      .binding {
        padding: 6px 0;
        border-top: 1px solid var(--divider-color);
      }
      .binding:first-of-type {
        border-top: none;
      }
      .entity-state-row {
        display: flex;
        justify-content: space-between;
        padding-left: 30px;
      }
      .entity ha-icon {
        color: var(--state-icon-color, var(--secondary-text-color));
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "clicker-device-page": ClickerDevicePage;
  }
}

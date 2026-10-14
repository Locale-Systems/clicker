// One device: its settings, its commands (test, edit, delete) and its entities.
// Changes go through the websocket API; the panel's data subscription brings
// the updated device back, so this view keeps no copy of its own.

import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { deleteCommand, errorMessage, sendCommand, updateCommand, updateDevice } from "./api";
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
import type { ClickerCommand, ClickerDevice, ClickerRadio, Hass } from "./types";

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
        </div>
        ${this.device.commands.length
          ? this.device.commands.map((c) => this._renderCommand(c, usage.get(c.id) ?? []))
          : html`<div class="meta">No commands yet. Learning comes next.</div>`}
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

  // --- Entities (read-only until the entity editor) ------------------------------

  private _renderEntities() {
    const rows = this.device.bindings.flatMap((b) =>
      (b.entity_ids.length ? b.entity_ids : [undefined]).map((entityId) => ({ b, entityId })),
    );
    return html`
      <div class="card">
        <div class="card-title">Entities</div>
        ${rows.length
          ? rows.map(({ b, entityId }) => {
              const st = entityId ? this.hass.states[entityId] : undefined;
              return html`<div class="entity">
                <ha-icon .icon=${PLATFORM_ICONS[b.platform] ?? "mdi:remote"}></ha-icon>
                <div class="row-main">
                  <div>${(st?.attributes.friendly_name as string | undefined) ?? b.name}</div>
                  <div class="meta">${entityId ?? "Not created"}</div>
                </div>
                <span class="meta">${entitySummary(st)}</span>
              </div>`;
            })
          : html`<div class="meta">No entities yet.</div>`}
      </div>
    `;
  }

  render() {
    return html`
      <div class="layout">
        <div class="column">${this._renderCommands()}</div>
        <div class="column">${this._renderSettings()} ${this._renderEntities()}</div>
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

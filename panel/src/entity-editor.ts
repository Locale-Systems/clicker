// Add or change one entity of a device: pick a template, name it, and pick a
// command for each role. The backend checks every change (binding/validate)
// and has the final say on save.

import { LitElement, css, html, nothing } from "lit";
import { property, state } from "lit/decorators.js";

import { createBinding, errorMessage, updateBinding, validateBinding } from "./api";
import { define } from "./define";
import { shared } from "./styles";
import {
  COVER_TYPES,
  TEMPLATES,
  buttonRole,
  detectTemplate,
  guessCoverType,
  slotsFor,
  speedCount,
  suggestRoles,
  templateById,
  type Template,
} from "./templates";
import type { ClickerBinding, ClickerDevice, Hass } from "./types";

const sentence = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

const PLATFORM_NAMES: Record<string, string> = {
  fan: "Fan",
  light: "Light",
  switch: "Switch",
  cover: "Cover",
  button: "Buttons",
};

@define("clicker-entity-editor")
export class ClickerEntityEditor extends LitElement {
  @property({ attribute: false }) hass!: Hass;
  @property({ attribute: false }) device!: ClickerDevice;
  /** The entity being changed; absent when adding one. */
  @property({ attribute: false }) binding?: ClickerBinding;

  @state() private _template!: Template;
  @state() private _name = "";
  @state() private _speeds = 0;
  @state() private _roles: Record<string, string> = {};
  @state() private _options: Record<string, string> = {};
  @state() private _check?: { ok: boolean; error: string | null };
  @state() private _saving = false;

  private _checkTimer?: number;

  connectedCallback(): void {
    super.connectedCallback();
    if (this.binding) {
      const { template, speeds } = detectTemplate(this.binding);
      this._template = template;
      this._speeds = speeds;
      this._name = this.binding.name;
      this._roles = { ...this.binding.roles };
      this._options = { ...(this.binding.options ?? {}) };
    } else {
      this._choose(TEMPLATES[0]);
    }
    this._scheduleCheck();
  }

  private _defaultName(template: Template): string {
    // Buttons take their commands' names; the group name is only a label.
    if (template.platform === "button") return PLATFORM_NAMES.button;
    const taken = this.device.bindings.some((b) => b.platform === template.platform);
    return taken ? PLATFORM_NAMES[template.platform] : this.device.name;
  }

  private _choose(template: Template): void {
    this._template = template;
    if (!this.binding) this._name = this._defaultName(template);
    this._speeds = template.hasSpeeds ? speedCount(this.device.commands) : 0;
    if (!this.binding) {
      const coverType = template.platform === "cover" ? guessCoverType(this.device.name) : "";
      this._options = coverType ? { device_class: coverType } : {};
    }
    this._roles = template.pickCommands
      ? {}
      : suggestRoles(slotsFor(template, this._speeds), this.device.commands);
    this._scheduleCheck();
  }

  private _setSpeeds(speeds: number): void {
    this._speeds = Math.max(0, Math.min(10, speeds || 0));
    const roles = Object.fromEntries(
      Object.entries(this._roles).filter(([role]) => {
        const n = /^speed_(\d+)$/.exec(role)?.[1];
        return !n || Number(n) <= this._speeds;
      }),
    );
    const suggested = suggestRoles(slotsFor(this._template, this._speeds), this.device.commands);
    for (const [role, id] of Object.entries(suggested)) if (!(role in roles)) roles[role] = id;
    this._roles = roles;
    this._scheduleCheck();
  }

  private _setRole(role: string, commandId: string): void {
    const roles = { ...this._roles };
    if (commandId) roles[role] = commandId;
    else delete roles[role];
    this._roles = roles;
    this._scheduleCheck();
  }

  private _setCoverType(value: string): void {
    this._options = value ? { device_class: value } : {};
    this._scheduleCheck();
  }

  private _toggleButton(commandId: string, name: string, on: boolean): void {
    const roles = Object.fromEntries(Object.entries(this._roles).filter(([, id]) => id !== commandId));
    if (on) roles[buttonRole(name, new Set(Object.keys(roles)))] = commandId;
    this._roles = roles;
    this._scheduleCheck();
  }

  private _scheduleCheck(): void {
    window.clearTimeout(this._checkTimer);
    this._check = undefined;
    this._checkTimer = window.setTimeout(async () => {
      try {
        this._check = await validateBinding(
          this.hass,
          this.device.id,
          this._template.platform,
          this._roles,
          this._options,
        );
      } catch (err) {
        this._check = { ok: false, error: errorMessage(err) };
      }
    }, 250);
  }

  private _close(): void {
    this.dispatchEvent(new CustomEvent("close"));
  }

  private async _save(): Promise<void> {
    this._saving = true;
    try {
      if (this.binding) {
        await updateBinding(this.hass, this.device.id, this.binding.id, {
          name: this._name.trim(),
          roles: this._roles,
          options: this._options,
        });
      } else {
        await createBinding(this.hass, this.device.id, {
          platform: this._template.platform,
          name: this._name.trim(),
          roles: this._roles,
          options: this._options,
        });
      }
      this.dispatchEvent(
        new CustomEvent("hass-notification", {
          detail: { message: this.binding ? "Saved" : `Added ${this._name.trim()}` },
          bubbles: true,
          composed: true,
        }),
      );
      this._close();
    } catch (err) {
      this._check = { ok: false, error: errorMessage(err) };
    }
    this._saving = false;
  }

  render() {
    const templates = this.binding
      ? TEMPLATES.filter((t) => t.platform === this.binding!.platform)
      : TEMPLATES;
    return html`
      <div class="editor">
        <label
          >Type
          <select
            @change=${(e: Event) => this._choose(templateById((e.target as HTMLSelectElement).value))}
          >
            ${templates.map(
              (t) => html`<option value=${t.id} ?selected=${t.id === this._template.id}>${t.label}</option>`,
            )}
          </select></label
        >
        <label
          >Name
          <input
            .value=${this._name}
            @input=${(e: Event) => (this._name = (e.target as HTMLInputElement).value)}
          />
          <span class="hint">
            ${this._name.trim().toLowerCase() === this.device.name.toLowerCase()
              ? "Shown as just the device name"
              : `Shown as ${this.device.name} ${this._name.trim()}`}
          </span></label
        >
        ${this._template.platform === "cover" ? this._renderCoverType() : nothing}
        ${this._template.hasSpeeds
          ? html`<label
              >Speeds
              <input
                type="number"
                min="0"
                max="10"
                .value=${String(this._speeds)}
                @input=${(e: Event) => this._setSpeeds(Number((e.target as HTMLInputElement).value))}
            /></label>`
          : nothing}
        ${this._template.pickCommands ? this._renderButtons() : this._renderSlots()}
        <div class="status ${this._check?.ok ? "ok" : this._check ? "error" : ""}">
          ${this._check
            ? this._check.ok
              ? "Ready to save"
              : sentence(this._check.error ?? "")
            : "Checking…"}
        </div>
        <div class="actions">
          <span class="spacer"></span>
          <button @click=${this._close}>Cancel</button>
          <button
            class="primary"
            ?disabled=${!this._check?.ok || !this._name.trim() || this._saving}
            @click=${this._save}
          >
            ${this.binding ? "Save" : "Add"}
          </button>
        </div>
      </div>
    `;
  }

  private _renderCoverType() {
    const current = this._options.device_class ?? "";
    return html`<label
      >Kind of cover
      <select @change=${(e: Event) => this._setCoverType((e.target as HTMLSelectElement).value)}>
        <option value="" ?selected=${!current}>Generic cover</option>
        ${COVER_TYPES.map(
          (t) => html`<option value=${t.value} ?selected=${t.value === current}>${t.label}</option>`,
        )}
      </select>
      <span class="hint">Sets the icon, and how voice assistants talk about it</span></label
    >`;
  }

  private _renderSlots() {
    return html`<div class="slots">
      ${slotsFor(this._template, this._speeds).map(
        (slot) => html`<label class="slot"
          ><span>${slot.label}${slot.required ? "" : html` <span class="optional">optional</span>`}</span>
          <select @change=${(e: Event) => this._setRole(slot.role, (e.target as HTMLSelectElement).value)}>
            <option value="" ?selected=${!this._roles[slot.role]}>${slot.required ? "Choose…" : "None"}</option>
            ${this.device.commands.map(
              (c) => html`<option value=${c.id} ?selected=${this._roles[slot.role] === c.id}>${c.name}</option>`,
            )}
          </select></label
        >`,
      )}
    </div>`;
  }

  private _renderButtons() {
    const chosen = new Set(Object.values(this._roles));
    return html`<div class="buttons">
      <span class="hint">Each command you pick becomes its own button entity.</span>
      ${this.device.commands.map(
        (c) => html`<label class="check"
          ><input
            type="checkbox"
            .checked=${chosen.has(c.id)}
            @change=${(e: Event) => this._toggleButton(c.id, c.name, (e.target as HTMLInputElement).checked)}
          />${c.name}</label
        >`,
      )}
    </div>`;
  }

  static styles = [
    shared,
    css`
      .editor {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 10px 0;
      }
      .slots {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      label.slot {
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        color: var(--primary-text-color);
        font-size: 14px;
      }
      label.slot select {
        min-width: 50%;
      }
      .optional {
        color: var(--secondary-text-color);
        font-size: 12px;
      }
      .buttons {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      label.check {
        flex-direction: row;
        align-items: center;
        gap: 8px;
        color: var(--primary-text-color);
        font-size: 14px;
      }
      .hint {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .status {
        font-size: 13px;
        color: var(--secondary-text-color);
      }
      .status.ok {
        color: var(--success-color);
      }
      .status.error {
        color: var(--error-color);
      }
      .actions {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .spacer {
        flex: 1;
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "clicker-entity-editor": ClickerEntityEditor;
  }
}

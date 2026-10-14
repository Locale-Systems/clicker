// The Clicker sidebar panel. Home Assistant creates <clicker-panel> and sets
// `hass`, `narrow` and `panel`; the panel keeps Clicker's data live through
// the clicker/data/subscribe websocket subscription.

import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import "./device-page";
import { count, entitySummary, groupByArea, radioLabel } from "./format";
import type { ClickerData, ClickerDevice, ClickerRadio, Hass } from "./types";

interface Route {
  prefix: string;
  path: string;
}

const PLATFORM_ICONS: Record<string, string> = {
  fan: "mdi:fan",
  light: "mdi:lightbulb",
  switch: "mdi:toggle-switch-variant",
  button: "mdi:gesture-tap-button",
};

@customElement("clicker-panel")
export class ClickerPanel extends LitElement {
  @property({ attribute: false }) hass?: Hass;
  @property({ type: Boolean }) narrow = false;
  @property({ attribute: false }) route?: Route;

  @state() private _data?: ClickerData;
  @state() private _error?: string;

  private _unsubscribe?: Promise<() => Promise<void>>;

  updated(changed: Map<string, unknown>): void {
    if (changed.has("hass") && this.hass && !this._unsubscribe) this._subscribe();
  }

  connectedCallback(): void {
    super.connectedCallback();
    if (this.hass && !this._unsubscribe) this._subscribe();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._unsubscribe?.then((unsubscribe) => unsubscribe()).catch(() => undefined);
    this._unsubscribe = undefined;
  }

  private _subscribe(): void {
    this._unsubscribe = this.hass!.connection.subscribeMessage<ClickerData>(
      (data) => {
        this._data = data;
        this._error = undefined;
      },
      { type: "clicker/data/subscribe" },
    );
    this._unsubscribe.catch((err: { message?: string }) => {
      this._error = err.message ?? "Clicker isn't responding. Check that it's loaded.";
      this._unsubscribe = undefined;
    });
  }

  /** Go to a path inside the panel, the way Home Assistant navigates. */
  private _navigate(path: string): void {
    history.pushState(null, "", `${this.route?.prefix ?? "/clicker"}${path}`);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
  }

  private get _deviceId(): string | undefined {
    return /^\/device\/([^/]+)/.exec(this.route?.path ?? "")?.[1];
  }

  render() {
    const deviceId = this._deviceId;
    const device = deviceId ? this._data?.devices.find((d) => d.id === deviceId) : undefined;
    if (deviceId && this._data && this.hass) {
      return html`
        <div class="toolbar">
          <button class="back" aria-label="Back to devices" @click=${() => this._navigate("")}>
            <ha-icon icon="mdi:arrow-left"></ha-icon>
          </button>
          <div class="title">${device?.name ?? "Device not found"}</div>
        </div>
        <div class="content">
          ${device
            ? html`<clicker-device-page
                .hass=${this.hass}
                .device=${device}
                .radios=${this._data.radios}
              ></clicker-device-page>`
            : html`<p class="notice">This device was deleted.</p>`}
        </div>
      `;
    }
    return html`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">Clicker</div>
      </div>
      <div class="content">${this._renderBody()}</div>
    `;
  }

  private _renderBody() {
    if (this._error) return html`<p class="notice error">${this._error}</p>`;
    if (!this._data || !this.hass) return html`<p class="notice">Loading…</p>`;
    const { devices, radios, problems } = this._data;
    if (!devices.length) {
      return html`<div class="empty">
        <h2>Set up your first remote</h2>
        <p>Clicker learns your RF remotes' buttons and turns them into fans, lights, switches and buttons.</p>
        <p class="hint">${radios.length
          ? `Radios ready: ${radios.map((r) => `${r.name}`).join(", ")}.`
          : "No radios yet. Clicker finds ESPHome radios with an RF transmitter or receiver."}</p>
      </div>`;
    }
    const radioById = new Map(radios.map((r) => [r.id, r]));
    return html`
      ${problems.length
        ? html`<div class="problems">${problems.map((p) => html`<div>${p}</div>`)}</div>`
        : nothing}
      ${groupByArea(devices, this.hass.areas).map(
        (group) => html`
          <h2 class="area">${group.name}</h2>
          <div class="grid">
            ${group.devices.map((d) => this._renderDevice(d, radioById.get(d.radio_id)))}
          </div>
        `,
      )}
    `;
  }

  private _renderDevice(device: ClickerDevice, radio: ClickerRadio | undefined) {
    const entities = device.bindings.flatMap((b) =>
      (b.entity_ids.length ? b.entity_ids : [undefined]).map((entityId) => ({ binding: b, entityId })),
    );
    return html`
      <div
        class="card clickable"
        role="button"
        tabindex="0"
        @click=${() => this._navigate(`/device/${device.id}`)}
        @keydown=${(e: KeyboardEvent) => e.key === "Enter" && this._navigate(`/device/${device.id}`)}
      >
        <div class="card-head">
          <span class="name">${device.name}</span>
          ${radio?.online
            ? nothing
            : html`<span class="badge warning">${radio ? "Radio offline" : "No radio"}</span>`}
        </div>
        <div class="meta">
          ${radioLabel(radio?.name, device.frequency_hz)} ·
          ${count(device.commands.length, "command")}
        </div>
        ${entities.length
          ? html`<div class="entities">
              ${entities.map(({ binding, entityId }) => {
                const state = entityId ? this.hass!.states[entityId] : undefined;
                const name =
                  (state?.attributes.friendly_name as string | undefined) ?? binding.name;
                return html`<div class="entity">
                  <ha-icon .icon=${PLATFORM_ICONS[binding.platform] ?? "mdi:remote"}></ha-icon>
                  <span class="entity-name">${name}</span>
                  <span class="entity-state">${entitySummary(state)}</span>
                </div>`;
              })}
            </div>`
          : html`<div class="meta">No entities yet</div>`}
      </div>
    `;
  }

  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--primary-background-color);
      color: var(--primary-text-color);
      font-family: var(--ha-font-family-body, Roboto, sans-serif);
    }
    .toolbar {
      display: flex;
      align-items: center;
      height: var(--header-height, 56px);
      padding: 0 12px;
      background: var(--app-header-background-color);
      color: var(--app-header-text-color, white);
      border-bottom: var(--app-header-border-bottom, none);
      box-sizing: border-box;
    }
    .title {
      margin-left: 12px;
      font-size: 20px;
    }
    .back {
      display: inline-flex;
      background: none;
      border: none;
      color: inherit;
      padding: 8px;
      cursor: pointer;
    }
    .clickable {
      cursor: pointer;
    }
    .clickable:hover,
    .clickable:focus-visible {
      border-color: var(--primary-color);
      outline: none;
    }
    .content {
      max-width: 1040px;
      margin: 0 auto;
      padding: 8px 16px 32px;
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
    .card {
      background: var(--card-background-color);
      border-radius: var(--ha-card-border-radius, 12px);
      border: 1px solid var(--divider-color);
      padding: 14px 16px;
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
    .meta {
      color: var(--secondary-text-color);
      font-size: 13px;
      margin-top: 4px;
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
      --mdc-icon-size: 20px;
    }
    .entity-name {
      flex: 1;
    }
    .entity-state {
      color: var(--secondary-text-color);
      font-size: 13px;
    }
    .badge {
      font-size: 12px;
      padding: 2px 8px;
      border-radius: 10px;
    }
    .badge.warning {
      color: var(--warning-color);
      border: 1px solid var(--warning-color);
    }
    .problems {
      margin: 12px 0;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid var(--warning-color);
      font-size: 14px;
    }
    .notice {
      color: var(--secondary-text-color);
      padding: 24px 4px;
    }
    .notice.error {
      color: var(--error-color);
    }
    .empty {
      text-align: center;
      padding: 48px 16px;
    }
    .empty h2 {
      font-weight: 400;
    }
    .hint {
      color: var(--secondary-text-color);
      font-size: 14px;
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "clicker-panel": ClickerPanel;
  }
}

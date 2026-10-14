// The Clicker sidebar panel. Home Assistant creates <clicker-panel> and sets
// `hass`, `narrow` and `route`; the panel keeps Clicker's data live through
// clicker/data/subscribe and routes between its pages:
//   ""                   devices
//   /signals, /radios    live signals, radios
//   /device/<id>[/learn] one device (optionally starting a learn session)

import { LitElement, css, html } from "lit";
import { property, state } from "lit/decorators.js";

import { errorMessage } from "./api";
import { define } from "./define";
import "./device-page";
import "./devices-page";
import "./radios-page";
import "./signals-page";
import type { ClickerData, Hass } from "./types";

const TABS = [
  { path: "", label: "Devices" },
  { path: "/signals", label: "Live signals" },
  { path: "/radios", label: "Radios" },
];

interface Route {
  prefix: string;
  path: string;
}

@define("clicker-panel")
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
    this._unsubscribe.catch((err) => {
      this._error = errorMessage(err);
      this._unsubscribe = undefined;
    });
  }

  /** Go to a path inside the panel, the way Home Assistant navigates. */
  private _navigate(path: string): void {
    history.pushState(null, "", `${this.route?.prefix ?? "/clicker"}${path}`);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
  }

  render() {
    const match = /^\/device\/([^/]+)(\/learn)?/.exec(this.route?.path ?? "");
    return match ? this._renderDevice(match[1], !!match[2]) : this._renderTabs();
  }

  private _renderDevice(deviceId: string, learn: boolean) {
    const device = this._data?.devices.find((d) => d.id === deviceId);
    return html`
      <div class="toolbar">
        <button class="back" aria-label="Back to devices" @click=${() => this._navigate("")}>
          <ha-icon icon="mdi:arrow-left"></ha-icon>
        </button>
        <div class="title">${device?.name ?? (this._data ? "Device not found" : "")}</div>
      </div>
      <div class="content">
        ${this._notice() ??
        (device
          ? html`<clicker-device-page
              .hass=${this.hass}
              .device=${device}
              .radios=${this._data!.radios}
              .learn=${learn}
            ></clicker-device-page>`
          : html`<p class="notice">This device was deleted.</p>`)}
      </div>
    `;
  }

  private _renderTabs() {
    const path = this.route?.path ?? "";
    const tab = TABS.find((t) => t.path && path.startsWith(t.path))?.path ?? "";
    return html`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">Clicker</div>
      </div>
      <div class="tabs" role="tablist">
        ${TABS.map(
          (t) => html`<button
            role="tab"
            class="tab ${t.path === tab ? "active" : ""}"
            aria-selected=${t.path === tab}
            @click=${() => this._navigate(t.path)}
          >
            ${t.label}
          </button>`,
        )}
      </div>
      <div class="content">${this._notice() ?? this._renderTab(tab)}</div>
    `;
  }

  private _notice() {
    if (this._error) return html`<p class="notice error">${this._error}</p>`;
    if (!this._data || !this.hass) return html`<p class="notice">Loading…</p>`;
    return undefined;
  }

  private _renderTab(tab: string) {
    if (tab === "/signals") {
      return html`<clicker-signals-page
        .hass=${this.hass}
        .radios=${this._data!.radios}
      ></clicker-signals-page>`;
    }
    if (tab === "/radios") {
      return html`<clicker-radios-page .hass=${this.hass} .data=${this._data}></clicker-radios-page>`;
    }
    return html`<clicker-devices-page
      .hass=${this.hass}
      .data=${this._data}
      @navigate=${(e: CustomEvent<{ path: string }>) => this._navigate(e.detail.path)}
    ></clicker-devices-page>`;
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
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .back {
      display: inline-flex;
      background: none;
      border: none;
      color: inherit;
      padding: 8px;
      cursor: pointer;
    }
    .tabs {
      display: flex;
      gap: 4px;
      padding: 0 16px;
      overflow-x: auto;
      background: var(--app-header-background-color);
      border-bottom: 1px solid var(--divider-color);
    }
    .tab {
      font: inherit;
      font-size: 14px;
      white-space: nowrap;
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--app-header-text-color, var(--secondary-text-color));
      opacity: 0.75;
      padding: 10px 12px;
      cursor: pointer;
    }
    .tab.active {
      opacity: 1;
      border-bottom-color: var(--primary-color);
    }
    .content {
      max-width: 1040px;
      margin: 0 auto;
      padding: 8px 16px 32px;
    }
    .notice {
      color: var(--secondary-text-color);
      padding: 24px 4px;
    }
    .notice.error {
      color: var(--error-color);
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "clicker-panel": ClickerPanel;
  }
}

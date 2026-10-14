// The learn drawer: a learn session for one device, open while the drawer is.
// Candidates arrive live from clicker/learn/subscribe as the remote is pressed;
// each can be tested, then saved as a new command or as the new code of an
// existing one.

import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { errorMessage, learnSave, learnTest } from "./api";
import { KIND_HINTS, KIND_LABELS, candidateMeta, candidateTitle, mhz } from "./format";
import { shared } from "./styles";
import type { ClickerDevice, Hass, LearnCandidate, LearnUpdate } from "./types";

interface SaveDraft {
  fingerprint: string;
  mode: "new" | "replace";
  name: string;
  kind: string;
  commandId: string;
}

@customElement("clicker-learn-drawer")
export class ClickerLearnDrawer extends LitElement {
  @property({ attribute: false }) hass!: Hass;
  @property({ attribute: false }) device!: ClickerDevice;

  @state() private _update?: LearnUpdate;
  @state() private _error?: string;
  @state() private _draft?: SaveDraft;
  @state() private _saved = new Map<string, string>(); // fingerprint -> command name
  @state() private _testing?: string;

  private _unsubscribe?: Promise<() => Promise<void>>;

  connectedCallback(): void {
    super.connectedCallback();
    this._unsubscribe = this.hass.connection.subscribeMessage<LearnUpdate>(
      (update) => {
        this._update = update;
      },
      { type: "clicker/learn/subscribe", device_id: this.device.id },
    );
    this._unsubscribe.catch((err) => (this._error = errorMessage(err)));
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._unsubscribe?.then((unsubscribe) => unsubscribe()).catch(() => undefined);
    this._unsubscribe = undefined;
  }

  private _toast(message: string): void {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }),
    );
  }

  private _close(): void {
    this.dispatchEvent(new CustomEvent("close"));
  }

  private async _test(candidate: LearnCandidate): Promise<void> {
    if (!this._update) return;
    this._testing = candidate.fingerprint;
    try {
      await learnTest(this.hass, this._update.session_id, candidate.fingerprint);
      this._toast("Sent. Did the device respond?");
    } catch (err) {
      this._toast(errorMessage(err));
    }
    this._testing = undefined;
  }

  private _startSave(candidate: LearnCandidate): void {
    this._draft = {
      fingerprint: candidate.fingerprint,
      mode: "new",
      name: "",
      kind: "button",
      commandId: this.device.commands[0]?.id ?? "",
    };
  }

  private _nameTaken(name: string): boolean {
    return this.device.commands.some((c) => c.name.toLowerCase() === name.trim().toLowerCase());
  }

  private async _save(): Promise<void> {
    const draft = this._draft;
    if (!draft || !this._update) return;
    const target =
      draft.mode === "new"
        ? { name: draft.name.trim(), kind: draft.kind }
        : { command_id: draft.commandId };
    try {
      const command = await learnSave(this.hass, this._update.session_id, draft.fingerprint, target);
      this._saved = new Map([...this._saved, [draft.fingerprint, command.name]]);
      this._draft = undefined;
      this._toast(draft.mode === "new" ? `Saved ${command.name}` : `Relearned ${command.name}`);
    } catch (err) {
      this._toast(errorMessage(err));
    }
  }

  render() {
    const frequency = this._update ? mhz(this._update.frequency_hz) : mhz(this.device.frequency_hz);
    const candidates = this._update?.candidates ?? [];
    return html`
      <div class="card learning">
        <div class="card-title">
          Learn <span class="spacer"></span>
          <button class="icon" aria-label="Stop learning" @click=${this._close}>
            <ha-icon icon="mdi:close"></ha-icon>
          </button>
        </div>
        ${this._error
          ? html`<div class="error">${this._error}</div>`
          : html`<div class="listening">
              <span class="dot"></span>
              ${this._update
                ? `Listening on ${frequency}. Press a button on the remote 2 or 3 times.`
                : "Starting…"}
            </div>`}
        ${candidates.map((c) => this._renderCandidate(c))}
      </div>
    `;
  }

  private _renderCandidate(candidate: LearnCandidate) {
    const saved = this._saved.get(candidate.fingerprint);
    const known = candidate.known_as.find((k) => k.device === this.device.name);
    const elsewhere = candidate.known_as.filter((k) => k.device !== this.device.name);
    const drafting = this._draft?.fingerprint === candidate.fingerprint;
    return html`
      <div class="candidate">
        <div class="candidate-head">
          <span class="candidate-title">${candidateTitle(candidate)}</span>
          ${saved
            ? html`<span class="chip success">Saved as ${saved}</span>`
            : known
              ? html`<span class="chip warning">Already ${known.command}</span>`
              : html`<span class="chip">New</span>`}
        </div>
        <div class="meta">${candidateMeta(candidate)}</div>
        ${elsewhere.length
          ? html`<div class="meta">
              Also sent by ${elsewhere.map((k) => `${k.device} / ${k.command}`).join(", ")}
            </div>`
          : nothing}
        ${drafting
          ? this._renderDraft(this._draft!)
          : candidate.usable
            ? html`<div class="actions">
                <button
                  ?disabled=${this._testing === candidate.fingerprint}
                  @click=${() => this._test(candidate)}
                >
                  ${this._testing === candidate.fingerprint ? "Sending…" : "Test"}
                </button>
                ${saved ? nothing : html`<button @click=${() => this._startSave(candidate)}>Save…</button>`}
              </div>`
            : nothing}
      </div>
    `;
  }

  private _renderDraft(draft: SaveDraft) {
    const set = (patch: Partial<SaveDraft>) => (this._draft = { ...draft, ...patch });
    const taken = draft.mode === "new" && this._nameTaken(draft.name);
    const ready = draft.mode === "new" ? !!draft.name.trim() && !taken : !!draft.commandId;
    return html`
      <div class="draft">
        <div class="modes">
          <label class="radio"
            ><input
              type="radio"
              name="mode"
              .checked=${draft.mode === "new"}
              @change=${() => set({ mode: "new" })}
            />New command</label
          >
          ${this.device.commands.length
            ? html`<label class="radio"
                ><input
                  type="radio"
                  name="mode"
                  .checked=${draft.mode === "replace"}
                  @change=${() => set({ mode: "replace" })}
                />Relearn an existing one</label
              >`
            : nothing}
        </div>
        ${draft.mode === "new"
          ? html`<label
                >Name
                <input
                  placeholder="Light"
                  .value=${draft.name}
                  @input=${(e: Event) => set({ name: (e.target as HTMLInputElement).value })}
                />
                ${taken ? html`<span class="hint error">${this.device.name} already has one</span>` : nothing}
              </label>
              <label
                >Kind
                <select @change=${(e: Event) => set({ kind: (e.target as HTMLSelectElement).value })}>
                  ${Object.entries(KIND_LABELS).map(
                    ([kind, label]) => html`<option value=${kind} ?selected=${kind === draft.kind}>
                      ${label}
                    </option>`,
                  )}
                </select>
                <span class="hint">${KIND_HINTS[draft.kind]}</span>
              </label>`
          : html`<label
              >Replace the code of
              <select @change=${(e: Event) => set({ commandId: (e.target as HTMLSelectElement).value })}>
                ${this.device.commands.map(
                  (c) => html`<option value=${c.id} ?selected=${c.id === draft.commandId}>${c.name}</option>`,
                )}
              </select>
            </label>`}
        <div class="actions">
          <span class="spacer"></span>
          <button @click=${() => (this._draft = undefined)}>Cancel</button>
          <button class="primary" ?disabled=${!ready} @click=${this._save}>
            ${draft.mode === "new" ? "Save" : "Relearn"}
          </button>
        </div>
      </div>
    `;
  }

  static styles = [
    shared,
    css`
      .learning {
        border-color: var(--primary-color);
      }
      .spacer {
        flex: 1;
      }
      .listening {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        color: var(--secondary-text-color);
        margin-bottom: 8px;
      }
      .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--primary-color);
        animation: pulse 1.6s ease-in-out infinite;
      }
      @keyframes pulse {
        50% {
          opacity: 0.25;
        }
      }
      .error {
        color: var(--error-color);
        font-size: 14px;
      }
      .candidate {
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 10px 12px;
        margin-top: 8px;
      }
      .candidate-head {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .candidate-title {
        flex: 1;
        font-weight: 500;
        font-family: var(--code-font-family, monospace);
        font-size: 14px;
      }
      .chip.success {
        color: var(--success-color);
        border-color: var(--success-color);
      }
      .actions {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 8px;
      }
      .draft {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-top: 10px;
      }
      .modes {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
      }
      label.radio {
        flex-direction: row;
        align-items: center;
        gap: 6px;
        font-size: 14px;
        color: var(--primary-text-color);
      }
      .hint {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .hint.error {
        color: var(--error-color);
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "clicker-learn-drawer": ClickerLearnDrawer;
  }
}

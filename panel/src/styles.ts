// Styles shared by the panel's views, from Home Assistant's theme variables.

import { css } from "lit";

export const shared = css`
  :host {
    color: var(--primary-text-color);
    font-family: var(--ha-font-family-body, Roboto, sans-serif);
  }
  .card {
    background: var(--card-background-color);
    border-radius: var(--ha-card-border-radius, 12px);
    border: 1px solid var(--divider-color);
    padding: 14px 16px;
  }
  .card-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 500;
    margin-bottom: 8px;
  }
  .meta {
    color: var(--secondary-text-color);
    font-size: 13px;
  }
  button {
    white-space: nowrap;
    font: inherit;
    font-size: 14px;
    color: var(--primary-color);
    background: none;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 6px 12px;
    cursor: pointer;
  }
  button:hover {
    background: var(--secondary-background-color);
  }
  button.primary {
    color: var(--text-primary-color, white);
    background: var(--primary-color);
    border-color: var(--primary-color);
  }
  button.danger {
    color: var(--error-color);
  }
  button.icon {
    border: none;
    padding: 6px;
    color: var(--secondary-text-color);
    display: inline-flex;
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  input,
  select {
    font: inherit;
    font-size: 14px;
    color: var(--primary-text-color);
    background: var(--secondary-background-color, transparent);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 7px 10px;
    box-sizing: border-box;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 13px;
    color: var(--secondary-text-color);
  }
  .chip {
    font-size: 12px;
    padding: 1px 8px;
    border-radius: 10px;
    border: 1px solid var(--divider-color);
    color: var(--secondary-text-color);
    white-space: nowrap;
  }
  .chip.warning {
    color: var(--warning-color);
    border-color: var(--warning-color);
  }
  ha-icon {
    --mdc-icon-size: 20px;
  }
`;

// What the panel reads from Home Assistant and from Clicker's websocket API.

export interface HassEntityState {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
}

export interface HassArea {
  area_id: string;
  name: string;
}

export interface HassConnection {
  subscribeMessage<T>(
    callback: (message: T) => void,
    message: Record<string, unknown>,
  ): Promise<() => Promise<void>>;
  sendMessagePromise<T>(message: Record<string, unknown>): Promise<T>;
}

export interface Hass {
  connection: HassConnection;
  states: Record<string, HassEntityState>;
  areas: Record<string, HassArea>;
  language: string;
}

export interface ClickerCommand {
  id: string;
  name: string;
  kind: "button" | "toggle" | "state";
  frames_on_air: number;
  captures: number;
  encoded: boolean;
  encoding?: string;
  reason?: string;
  bits: string | null;
}

export interface ClickerBinding {
  id: string;
  platform: string;
  name: string;
  roles: Record<string, string>;
  entity_ids: string[];
}

export interface ClickerDevice {
  id: string;
  name: string;
  radio_id: string;
  frequency_hz: number;
  area_id: string | null;
  ha_device_id: string | null;
  commands: ClickerCommand[];
  bindings: ClickerBinding[];
}

export interface ClickerRadio {
  id: string;
  name: string;
  frequency_hz: number;
  online: boolean;
  node: string | null;
  can_send: boolean;
  can_receive: boolean;
}

export interface ClickerData {
  radios: ClickerRadio[];
  devices: ClickerDevice[];
  problems: string[];
}

export interface LearnCandidate {
  fingerprint: string;
  bits: string | null;
  encoding: string | null;
  how: string;
  sightings: number;
  variants: number;
  first_at: number;
  last_at: number;
  usable: boolean;
  encoded: boolean;
  known_as: { device: string; command: string; distance: number }[];
}

export interface LearnUpdate {
  session_id: string;
  frequency_hz: number;
  candidates: LearnCandidate[];
}

export interface Heard {
  at: number; // seconds since the epoch
  radio_id: string;
  pulses: number;
  bits: string | null;
  encoding: string | null;
  fingerprint: string | null;
  how: string;
  matches: string[];
}

export interface RadioStats {
  heard: number;
  decoded: number;
  matched: number;
}

export interface ReceptionsUpdate {
  heard: Heard[];
  stats: Record<string, RadioStats>;
  window_s: number;
}

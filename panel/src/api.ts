// Clicker's websocket commands, typed. Errors reject with {code, message}.

import type { ClickerCommand, ClickerDevice, Hass } from "./types";

export interface SendResult {
  command: string;
  radio: string;
  encoded: boolean;
  frames_on_air: number;
  airtime_ms: number;
  waited_ms: number;
}

export const sendCommand = (hass: Hass, deviceId: string, commandId: string) =>
  hass.connection.sendMessagePromise<SendResult>({
    type: "clicker/command/send",
    device_id: deviceId,
    command_id: commandId,
  });

export const updateCommand = (
  hass: Hass,
  deviceId: string,
  commandId: string,
  changes: { name?: string; kind?: string; frames_on_air?: number },
) =>
  hass.connection.sendMessagePromise<ClickerCommand>({
    type: "clicker/command/update",
    device_id: deviceId,
    command_id: commandId,
    ...changes,
  });

export const deleteCommand = (hass: Hass, deviceId: string, commandId: string) =>
  hass.connection.sendMessagePromise<null>({
    type: "clicker/command/delete",
    device_id: deviceId,
    command_id: commandId,
  });

export const updateDevice = (
  hass: Hass,
  deviceId: string,
  changes: { name?: string; area_id?: string | null; radio_id?: string },
) =>
  hass.connection.sendMessagePromise<ClickerDevice>({
    type: "clicker/device/update",
    device_id: deviceId,
    ...changes,
  });

/** The message of a rejected websocket call. */
export function errorMessage(err: unknown): string {
  const message = (err as { message?: unknown } | undefined)?.message;
  return typeof message === "string" && message ? message : "Something went wrong. Try again.";
}

export const learnTest = (hass: Hass, sessionId: string, fingerprint: string) =>
  hass.connection.sendMessagePromise<SendResult>({
    type: "clicker/learn/test",
    session_id: sessionId,
    fingerprint,
  });

/** Save a candidate as a new command (name) or as the new code of command_id. */
export const learnSave = (
  hass: Hass,
  sessionId: string,
  fingerprint: string,
  target: { name: string; kind: string } | { command_id: string },
) =>
  hass.connection.sendMessagePromise<ClickerCommand>({
    type: "clicker/learn/save",
    session_id: sessionId,
    fingerprint,
    ...target,
  });

export const validateBinding = (
  hass: Hass,
  deviceId: string,
  platform: string,
  roles: Record<string, string>,
  options: Record<string, string> = {},
) =>
  hass.connection.sendMessagePromise<{ ok: boolean; error: string | null }>({
    type: "clicker/binding/validate",
    device_id: deviceId,
    platform,
    roles,
    options,
  });

export const createBinding = (
  hass: Hass,
  deviceId: string,
  binding: {
    platform: string;
    name: string;
    roles: Record<string, string>;
    options?: Record<string, string>;
  },
) =>
  hass.connection.sendMessagePromise<{ id: string }>({
    type: "clicker/binding/create",
    device_id: deviceId,
    ...binding,
  });

export const updateBinding = (
  hass: Hass,
  deviceId: string,
  bindingId: string,
  changes: { name?: string; roles?: Record<string, string>; options?: Record<string, string> },
) =>
  hass.connection.sendMessagePromise<{ id: string }>({
    type: "clicker/binding/update",
    device_id: deviceId,
    binding_id: bindingId,
    ...changes,
  });

export const deleteBinding = (hass: Hass, deviceId: string, bindingId: string) =>
  hass.connection.sendMessagePromise<null>({
    type: "clicker/binding/delete",
    device_id: deviceId,
    binding_id: bindingId,
  });

export const renameRadio = (hass: Hass, radioId: string, name: string) =>
  hass.connection.sendMessagePromise<unknown>({ type: "clicker/radio/update", radio_id: radioId, name });

export const deleteRadio = (hass: Hass, radioId: string) =>
  hass.connection.sendMessagePromise<null>({ type: "clicker/radio/delete", radio_id: radioId });

export const ignoreSource = (hass: Hass, sourceId: string, name: string) =>
  hass.connection.sendMessagePromise<{ id: string }>({
    type: "clicker/source/ignore",
    source_id: sourceId,
    name,
  });

export const unignoreSource = (hass: Hass, ignoredId: string) =>
  hass.connection.sendMessagePromise<null>({ type: "clicker/source/unignore", ignored_id: ignoredId });

export const createDevice = (
  hass: Hass,
  device: { name: string; radio_id: string; area_id?: string | null },
) => hass.connection.sendMessagePromise<ClickerDevice>({ type: "clicker/device/create", ...device });

export const importStatus = (hass: Hass) =>
  hass.connection.sendMessagePromise<{ available: boolean }>({ type: "clicker/import/status" });

export const importRun = (hass: Hass) =>
  hass.connection.sendMessagePromise<{ notes: string[]; problems: string[] }>({
    type: "clicker/import/run",
  });

export const deleteDevice = (hass: Hass, deviceId: string) =>
  hass.connection.sendMessagePromise<null>({ type: "clicker/device/delete", device_id: deviceId });

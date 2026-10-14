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

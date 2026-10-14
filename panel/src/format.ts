// Pure helpers for what the panel shows; tested in test/format.test.ts.

import type { ClickerDevice, HassArea, HassEntityState } from "./types";

export function mhz(frequencyHz: number): string {
  return `${(frequencyHz / 1e6).toFixed(2)} MHz`;
}

/** A radio as one label, without repeating a frequency its name already has. */
export function radioLabel(name: string | undefined, frequencyHz: number): string {
  const frequency = mhz(frequencyHz);
  if (!name) return frequency;
  return name.includes(frequency) ? name : `${name} · ${frequency}`;
}

export interface AreaGroup {
  areaId: string | null;
  name: string;
  devices: ClickerDevice[];
}

/** Devices grouped by area, areas by name, devices without an area last. */
export function groupByArea(
  devices: ClickerDevice[],
  areas: Record<string, HassArea>,
  noArea = "No area",
): AreaGroup[] {
  const groups = new Map<string | null, AreaGroup>();
  for (const device of devices) {
    const areaId = device.area_id && areas[device.area_id] ? device.area_id : null;
    let group = groups.get(areaId);
    if (!group) {
      group = { areaId, name: areaId ? areas[areaId].name : noArea, devices: [] };
      groups.set(areaId, group);
    }
    group.devices.push(device);
  }
  const byName = (a: { name: string }, b: { name: string }) =>
    a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  const sorted = [...groups.values()].sort((a, b) =>
    a.areaId === null ? 1 : b.areaId === null ? -1 : byName(a, b),
  );
  for (const group of sorted) group.devices.sort(byName);
  return sorted;
}

/** A short state for an entity row: "On, 25%", "Off", "Unavailable". */
export function entitySummary(state: HassEntityState | undefined): string {
  if (!state) return "Not created";
  switch (state.state) {
    case "unavailable":
      return "Unavailable";
    case "on": {
      const percentage = state.attributes.percentage;
      return typeof percentage === "number" ? `On, ${percentage}%` : "On";
    }
    case "off":
      return "Off";
    default:
      // Buttons hold the time of their last press.
      return state.entity_id.startsWith("button.") ? "" : state.state;
  }
}

/** "1 command", "6 commands". */
export function count(n: number, singular: string, plural = `${singular}s`): string {
  return `${n} ${n === 1 ? singular : plural}`;
}

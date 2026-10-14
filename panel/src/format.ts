// Pure helpers for what the panel shows; tested in test/format.test.ts.

import type {
  ClickerDevice,
  ClickerRadio,
  HassArea,
  HassEntityState,
  Heard,
  LearnCandidate,
  RadioStats,
  Source,
} from "./types";

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

export const KIND_LABELS: Record<string, string> = {
  button: "Button",
  toggle: "Toggle",
  state: "State",
};

export const KIND_HINTS: Record<string, string> = {
  button: "Always sent; no state",
  toggle: "Flips the state; sent only to change it",
  state: "Sets one state; safe to resend",
};

export interface Usage {
  bindingName: string;
  platform: string;
  role: string;
}

/** Which bindings (entities) use each command, by command id. */
export function commandUsage(device: ClickerDevice): Map<string, Usage[]> {
  const usage = new Map<string, Usage[]>();
  for (const binding of device.bindings) {
    for (const [role, commandId] of Object.entries(binding.roles)) {
      const list = usage.get(commandId) ?? [];
      list.push({ bindingName: binding.name, platform: binding.platform, role });
      usage.set(commandId, list);
    }
  }
  return usage;
}

/** "Patio Fan (fan), Scenes (button)" — each entity once. */
export function describeUsage(usages: Usage[]): string {
  const seen = new Set<string>();
  const parts: string[] = [];
  for (const u of usages) {
    const label = `${u.bindingName} (${u.platform})`;
    if (!seen.has(label)) {
      seen.add(label);
      parts.push(label);
    }
  }
  return parts.join(", ");
}

/** Radios a device can use: the ones on its frequency, its own first. */
export function radiosFor(device: ClickerDevice, radios: ClickerRadio[]): ClickerRadio[] {
  return radios
    .filter((r) => r.frequency_hz === device.frequency_hz)
    .sort((a, b) => (a.id === device.radio_id ? -1 : b.id === device.radio_id ? 1 : a.name.localeCompare(b.name)));
}

/** "24-bit code …00010000", or "Raw code" when it didn't decode. */
export function candidateTitle(candidate: LearnCandidate): string {
  if (!candidate.bits) return "Raw code";
  const tail = candidate.bits.slice(-8);
  return `${candidate.bits.length}-bit code ${candidate.bits.length > 8 ? "…" : ""}${tail}`;
}

/** "Encoded · seen 3× · 2 variants" */
export function candidateMeta(candidate: LearnCandidate): string {
  const parts = [
    candidate.usable ? (candidate.encoded ? "Encoded" : "Raw replay") : "Too short to use",
    `seen ${candidate.sightings}×`,
  ];
  if (candidate.variants > 1) parts.push(`${candidate.variants} variants`);
  return parts.join(" · ");
}

/** "24-bit …00000001", "Undecoded (48 pulses)" */
export function heardTitle(heard: Heard): string {
  if (!heard.bits) return `Undecoded (${heard.pulses} pulses)`;
  const tail = heard.bits.slice(-8);
  return `${heard.bits.length}-bit ${heard.bits.length > 8 ? "…" : ""}${tail}`;
}

/** "every ~50 s" / "every ~2 min", or how often it was heard when irregular. */
export function sourceRhythm(source: Source): string {
  if (source.period_s === null) return count(source.count, "time");
  const seconds = Math.round(source.period_s);
  const every = seconds < 120 ? `${seconds} s` : `${Math.round(seconds / 60)} min`;
  return `every ~${every} · ${count(source.count, "time")}`;
}

/** "12 heard · 3 matched · 9 undecoded" over the stats window. */
export function statsLine(stats: RadioStats | undefined): string {
  if (!stats || !stats.heard) return "Nothing heard";
  const undecoded = stats.heard - stats.decoded;
  const parts = [`${stats.heard} heard`, `${stats.matched} matched`];
  if (undecoded) parts.push(`${undecoded} undecoded`);
  return parts.join(" · ");
}

/** Advice for a radio, worst first. */
export function radioHints(radio: ClickerRadio, devices: number): string[] {
  const hints: string[] = [];
  if (!radio.online) {
    hints.push("Offline. Check that its ESPHome node is on and connected to Home Assistant.");
  }
  if (!radio.can_send) {
    hints.push("Can't send: its node has no RF transmitter on this frequency.");
  }
  if (!radio.can_receive) {
    hints.push("Can't hear remotes: add an RF receiver so remote presses update Home Assistant.");
  }
  if (!devices && radio.online && radio.can_send) hints.push("Ready for a device.");
  return hints;
}

export const PLATFORM_ICONS: Record<string, string> = {
  fan: "mdi:fan",
  light: "mdi:lightbulb",
  switch: "mdi:toggle-switch-variant",
  cover: "mdi:window-shutter",
  button: "mdi:gesture-tap-button",
};

/** "Imported 2 devices · skipped 1 already in Clicker" from the import's notes. */
export function importSummary(notes: string[]): string {
  const imported = notes.filter((n) => /: imported with \d+ commands?$/.test(n)).length;
  const skipped = notes.filter((n) => /: skipped, a device with that name exists$/.test(n)).length;
  if (!imported && !skipped) return "Nothing to import";
  const parts = [];
  if (imported) parts.push(`Imported ${count(imported, "device")}`);
  if (skipped) parts.push(`${imported ? "skipped" : "Skipped"} ${skipped} already in Clicker`);
  return parts.join(" · ");
}

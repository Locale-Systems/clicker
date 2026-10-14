// Entity templates: which roles an entity type needs, how to guess them from
// command names, and how to recognize the template of an existing binding.
// The backend has the final say (clicker/binding/validate).

import type { ClickerBinding, ClickerCommand } from "./types";

export interface RoleSlot {
  role: string;
  label: string;
  required: boolean;
}

export interface Template {
  id: string;
  platform: "fan" | "light" | "switch" | "button";
  label: string;
  hasSpeeds?: boolean;
  /** Buttons: pick any commands instead of filling slots. */
  pickCommands?: boolean;
  slots: RoleSlot[];
}

const OSCILLATE: RoleSlot = { role: "oscillate", label: "Oscillate (toggle)", required: false };
const REVERSE: RoleSlot = { role: "direction", label: "Reverse (toggle)", required: false };

export const TEMPLATES: Template[] = [
  {
    id: "fan_toggle",
    platform: "fan",
    label: "Fan with a power toggle",
    hasSpeeds: true,
    slots: [{ role: "power", label: "Power (toggle)", required: true }, OSCILLATE, REVERSE],
  },
  {
    id: "fan_off",
    platform: "fan",
    label: "Fan with an Off button",
    hasSpeeds: true,
    slots: [
      { role: "off", label: "Off", required: true },
      { role: "on", label: "On", required: false },
      OSCILLATE,
      REVERSE,
    ],
  },
  {
    id: "light_toggle",
    platform: "light",
    label: "Light with one toggle button",
    slots: [{ role: "toggle", label: "Toggle", required: true }],
  },
  {
    id: "light_onoff",
    platform: "light",
    label: "Light with On and Off buttons",
    slots: [
      { role: "on", label: "On", required: true },
      { role: "off", label: "Off", required: true },
    ],
  },
  {
    id: "switch_toggle",
    platform: "switch",
    label: "Switch with one toggle button",
    slots: [{ role: "toggle", label: "Toggle", required: true }],
  },
  {
    id: "switch_onoff",
    platform: "switch",
    label: "Switch with On and Off buttons",
    slots: [
      { role: "on", label: "On", required: true },
      { role: "off", label: "Off", required: true },
    ],
  },
  { id: "buttons", platform: "button", label: "Buttons", pickCommands: true, slots: [] },
];

export const templateById = (id: string) => TEMPLATES.find((t) => t.id === id)!;

/** The template's slots, with speed_1..speed_n first for a fan with speeds. */
export function slotsFor(template: Template, speeds: number): RoleSlot[] {
  const speedSlots = template.hasSpeeds
    ? Array.from({ length: speeds }, (_, i) => ({
        role: `speed_${i + 1}`,
        label: `Speed ${i + 1}`,
        required: true,
      }))
    : [];
  // Power buttons first, then speeds, then the optional toggles.
  const power = template.slots.filter((s) => s.required || s.role === "on");
  const rest = template.slots.filter((s) => !power.includes(s));
  return [...power, ...speedSlots, ...rest];
}

const PATTERNS: Record<string, RegExp> = {
  power: /power|on\s*\/\s*off/i,
  off: /^(fan\s+)?off$/i,
  on: /^(fan\s+)?on$/i,
  toggle: /light|lamp|toggle|power/i,
  oscillate: /oscillat|swing/i,
  direction: /reverse|direction/i,
};

/** Guess a command for each slot from command names; unmatched slots stay empty. */
export function suggestRoles(slots: RoleSlot[], commands: ClickerCommand[]): Record<string, string> {
  const roles: Record<string, string> = {};
  const used = new Set<string>();
  for (const slot of slots) {
    const speed = /^speed_(\d+)$/.exec(slot.role)?.[1];
    const pattern = speed ? new RegExp(`^(speed\\s*)?${speed}$`, "i") : PATTERNS[slot.role];
    const match = pattern && commands.find((c) => !used.has(c.id) && pattern.test(c.name.trim()));
    if (match) {
      roles[slot.role] = match.id;
      used.add(match.id);
    }
  }
  return roles;
}

/** Recognize an existing binding's template and its number of speeds. */
export function detectTemplate(binding: ClickerBinding): { template: Template; speeds: number } {
  const roles = Object.keys(binding.roles);
  const speeds = roles.filter((r) => /^speed_\d+$/.test(r)).length;
  const id =
    binding.platform === "fan"
      ? roles.includes("power") ? "fan_toggle" : "fan_off"
      : binding.platform === "button"
        ? "buttons"
        : `${binding.platform}_${roles.includes("on") && roles.includes("off") ? "onoff" : "toggle"}`;
  return { template: templateById(id), speeds };
}

/** A stable role key for a button, from its command's name. */
export function buttonRole(name: string, taken: Set<string>): string {
  const base = name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "button";
  let role = base;
  for (let n = 2; taken.has(role); n++) role = `${base}_${n}`;
  return role;
}

/** How many speed buttons a remote seems to have: Speed 1..n (or 1..n) in a row. */
export function speedCount(commands: ClickerCommand[]): number {
  let n = 0;
  while (commands.some((c) => new RegExp(`^(speed\\s*)?${n + 1}$`, "i").test(c.name.trim()))) n++;
  return n;
}

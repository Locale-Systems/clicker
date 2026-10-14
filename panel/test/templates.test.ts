import { describe, expect, it } from "vitest";
import {
  buttonRole,
  detectTemplate,
  slotsFor,
  speedCount,
  suggestRoles,
  templateById,
} from "../src/templates";
import type { ClickerCommand } from "../src/types";

const command = (id: string, name: string): ClickerCommand => ({
  id, name, kind: "state", frames_on_air: 8, captures: 1, encoded: true, bits: null,
});
const PATIO = ["Power", "Speed 1", "Speed 2", "Speed 3", "Speed 4", "Oscillate", "Nature"].map(
  (name, i) => command(`c${i}`, name),
);

describe("templates", () => {
  it("lays out a fan's slots: power, speeds, then the optional toggles", () => {
    const slots = slotsFor(templateById("fan_toggle"), 2);
    expect(slots.map((s) => s.role)).toEqual(["power", "speed_1", "speed_2", "oscillate", "direction"]);
    const off = slotsFor(templateById("fan_off"), 1).map((s) => s.role);
    expect(off).toEqual(["off", "on", "speed_1", "oscillate", "direction"]);
  });

  it("suggests the patio fan's commands by name", () => {
    const roles = suggestRoles(slotsFor(templateById("fan_toggle"), 4), PATIO);
    expect(roles).toEqual({
      power: "c0", speed_1: "c1", speed_2: "c2", speed_3: "c3", speed_4: "c4", oscillate: "c5",
    });
  });

  it("suggests a Minka-style remote", () => {
    const minka = ["Off", "1", "2", "3", "Reverse", "Light"].map((n, i) => command(`m${i}`, n));
    expect(suggestRoles(slotsFor(templateById("fan_off"), 3), minka)).toEqual({
      off: "m0", speed_1: "m1", speed_2: "m2", speed_3: "m3", direction: "m4",
    });
    expect(suggestRoles(slotsFor(templateById("light_toggle"), 0), minka)).toEqual({ toggle: "m5" });
  });

  it("recognizes existing bindings", () => {
    const fan = { id: "b", platform: "fan", name: "F", entity_ids: [], roles: { power: "a", speed_1: "b", speed_2: "c" } };
    expect(detectTemplate(fan)).toMatchObject({ template: { id: "fan_toggle" }, speeds: 2 });
    const light = { ...fan, platform: "light", roles: { on: "a", off: "b" } };
    expect(detectTemplate(light).template.id).toBe("light_onoff");
    expect(detectTemplate({ ...fan, platform: "switch", roles: { toggle: "a" } }).template.id).toBe("switch_toggle");
  });

  it("makes stable button roles", () => {
    const taken = new Set(["nature"]);
    expect(buttonRole("Nature", taken)).toBe("nature_2");
    expect(buttonRole("Breeze mode!", taken)).toBe("breeze_mode");
    expect(buttonRole("***", new Set())).toBe("button");
  });

  it("counts a remote's speed buttons", () => {
    expect(speedCount(PATIO)).toBe(4);
    expect(speedCount([command("a", "1"), command("b", "2"), command("c", "4")])).toBe(2);
    expect(speedCount([command("a", "Power")])).toBe(0);
  });
});

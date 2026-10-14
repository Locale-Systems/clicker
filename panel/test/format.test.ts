import { describe, expect, it } from "vitest";
import { count, entitySummary, groupByArea, mhz, radioLabel } from "../src/format";
import type { ClickerDevice } from "../src/types";

const device = (name: string, area_id: string | null): ClickerDevice => ({
  id: name,
  name,
  radio_id: "r",
  frequency_hz: 433_920_000,
  area_id,
  ha_device_id: null,
  commands: [],
  bindings: [],
});

describe("format", () => {
  it("shows frequencies in MHz", () => {
    expect(mhz(433_920_000)).toBe("433.92 MHz");
    expect(mhz(303_870_000)).toBe("303.87 MHz");
  });

  it("labels radios without repeating the frequency", () => {
    expect(radioLabel("wESP32 RF Gateway 433.92 MHz", 433_920_000)).toBe("wESP32 RF Gateway 433.92 MHz");
    expect(radioLabel("Garage", 303_870_000)).toBe("Garage · 303.87 MHz");
    expect(radioLabel(undefined, 433_920_000)).toBe("433.92 MHz");
  });

  it("groups devices by area name, unknown areas and none last", () => {
    const areas = {
      patio: { area_id: "patio", name: "Patio" },
      bed: { area_id: "bed", name: "bedroom" },
    };
    const groups = groupByArea(
      [device("Patio fan", "patio"), device("Lamp", null), device("Ceiling", "bed"), device("Old", "gone")],
      areas,
    );
    expect(groups.map((g) => [g.name, g.devices.map((d) => d.name)])).toEqual([
      ["bedroom", ["Ceiling"]],
      ["Patio", ["Patio fan"]],
      ["No area", ["Lamp", "Old"]],
    ]);
  });

  it("summarizes entity states", () => {
    const fan = { entity_id: "fan.f", state: "on", attributes: { percentage: 25 } };
    expect(entitySummary(fan)).toBe("On, 25%");
    expect(entitySummary({ entity_id: "light.l", state: "on", attributes: {} })).toBe("On");
    expect(entitySummary({ entity_id: "fan.f", state: "off", attributes: {} })).toBe("Off");
    expect(entitySummary({ entity_id: "button.b", state: "2026-10-13T12:00:00", attributes: {} })).toBe("");
    expect(entitySummary(undefined)).toBe("Not created");
  });

  it("counts", () => {
    expect(count(1, "command")).toBe("1 command");
    expect(count(6, "command")).toBe("6 commands");
  });
});

import { describe, expect, it } from "vitest";
import {
  candidateMeta,
  candidateTitle,
  commandUsage,
  count,
  describeUsage,
  entitySummary,
  groupByArea,
  heardTitle,
  importSummary,
  mhz,
  radioHints,
  radioLabel,
  radiosFor,
  sourceRhythm,
  statsLine,
} from "../src/format";
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

  it("finds which entities use a command", () => {
    const fan = device("Patio fan", null);
    fan.bindings = [
      { id: "b1", platform: "fan", name: "Patio fan", roles: { power: "p", speed_1: "s1" }, entity_ids: [], options: {} },
      { id: "b2", platform: "button", name: "Extras", roles: { press: "p" }, entity_ids: [], options: {} },
    ];
    const usage = commandUsage(fan);
    expect(describeUsage(usage.get("p")!)).toBe("Patio fan (fan), Extras (button)");
    expect(usage.get("s1")!.map((u) => u.role)).toEqual(["speed_1"]);
    expect(usage.get("other")).toBeUndefined();
  });

  it("offers radios on the device's frequency, its own first", () => {
    const radio = (id: string, name: string, frequency_hz: number) => ({
      id, name, frequency_hz, online: true, node: null, can_send: true, can_receive: true,
    });
    const fan = device("Fan", null);
    fan.radio_id = "own";
    const choices = radiosFor(fan, [
      radio("a", "Attic", 433_920_000),
      radio("own", "Garage", 433_920_000),
      radio("m", "Minka", 303_870_000),
    ]);
    expect(choices.map((r) => r.id)).toEqual(["own", "a"]);
  });

  it("describes learn candidates", () => {
    const candidate = {
      fingerprint: "24b:x",
      bits: "000001111000101100010000",
      encoding: "pwm",
      how: "6 complete frame(s), 6 agree on the bits",
      sightings: 4,
      variants: 1,
      first_at: 0,
      last_at: 0,
      usable: true,
      encoded: true,
      known_as: [],
    };
    expect(candidateTitle(candidate)).toBe("24-bit code …00010000");
    expect(candidateMeta(candidate)).toBe("Encoded · seen 4×");
    const raw = { ...candidate, bits: null, encoded: false, variants: 2, sightings: 1 };
    expect(candidateTitle(raw)).toBe("Raw code");
    expect(candidateMeta(raw)).toBe("Raw replay · seen 1× · 2 variants");
    expect(candidateMeta({ ...raw, usable: false })).toBe("Too short to use · seen 1× · 2 variants");
  });

  it("describes what the radios heard", () => {
    const heard = {
      at: 0, radio_id: "r", pulses: 250, bits: "000001111000101100000001", encoding: "pwm",
      fingerprint: "x", how: "", matches: ["Patio Fan / Power"], source_id: null,
    };
    expect(heardTitle(heard)).toBe("24-bit …00000001");
    expect(heardTitle({ ...heard, bits: null, pulses: 48 })).toBe("Undecoded (48 pulses)");
    expect(statsLine({ heard: 12, decoded: 3, matched: 2 })).toBe("12 heard · 2 matched · 9 undecoded");
    expect(statsLine({ heard: 2, decoded: 2, matched: 2 })).toBe("2 heard · 2 matched");
    expect(statsLine(undefined)).toBe("Nothing heard");
  });

  it("says how often a source transmits", () => {
    const source = {
      id: "s", label: "Source A", radio_id: "r", description: "", decoded: false, count: 12,
      first_seen: 0, last_seen: 600, period_s: 49.6, ignored_id: null,
    };
    expect(sourceRhythm(source)).toBe("every ~50 s · 12 times");
    expect(sourceRhythm({ ...source, period_s: 300 })).toBe("every ~5 min · 12 times");
    expect(sourceRhythm({ ...source, period_s: null, count: 2 })).toBe("2 times");
  });

  it("gives radio hints, worst first", () => {
    const radio = { id: "r", name: "R", frequency_hz: 1, online: true, node: "n", can_send: true, can_receive: true };
    expect(radioHints(radio, 1)).toEqual([]);
    expect(radioHints(radio, 0)).toEqual(["Ready for a device."]);
    const offline = radioHints({ ...radio, online: false, can_receive: false }, 1);
    expect(offline[0]).toMatch(/^Offline/);
    expect(offline[1]).toMatch(/^Can't hear remotes/);
  });

  it("summarizes an import", () => {
    expect(importSummary(["Patio Fan: imported with 6 commands", "Den: skipped, a device with that name exists"]))
      .toBe("Imported 1 device · skipped 1 already in Clicker");
    expect(importSummary(["Patio Fan / Power: toggle, encoded", "Patio Fan: skipped, a device with that name exists"]))
      .toBe("Skipped 1 already in Clicker");
    expect(importSummary([])).toBe("Nothing to import");
  });
});

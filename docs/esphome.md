# Setting up an ESPHome radio

Clicker sends and receives through ESPHome nodes. A node needs:

- an RF transceiver for your remote's frequency, such as a CC1101 module (300–348, 387–464 and 779–928 MHz);
- an ESPHome `remote_transmitter`, and ideally a `remote_receiver`, wired to the transceiver;
- a `radio_frequency` transmitter (and receiver) using the `ir_rf_proxy` platform, on the same frequency. These are what Home Assistant and Clicker see.

Add the node to Home Assistant's ESPHome integration as usual. Clicker finds its radios by itself and pairs the transmitter and receiver that share a frequency into one radio.

Without a receiver, Clicker can still send, but it can't learn new buttons or follow the physical remote.

## Example: CC1101 on a wESP32 (433.92 MHz)

This is a working configuration for a [Silicognition wESP32](https://wesp32.com/) (Ethernet and PoE) with a CC1101 module. For another ESP32 board, replace the `esp32` and `ethernet` sections with your board's (or `wifi:`), and adjust the pins.

| CC1101 | ESP32 |
| --- | --- |
| SCK | GPIO14 |
| MOSI | GPIO13 |
| MISO | GPIO12 |
| CSN | GPIO15 |
| GDO0 (data out to the radio: transmit) | GPIO4 |
| GDO2 (data in from the radio: receive) | GPIO5 |
| VCC | 3.3 V (not 5 V) |
| GND | GND |

```yaml
esphome:
  name: wesp32-rf-gateway
  friendly_name: "wESP32 RF Gateway"

esp32:
  board: esp32dev
  framework:
    type: esp-idf

# The wESP32's Ethernet (rev 7). Use wifi: instead on other boards.
ethernet:
  type: RTL8201
  mdc_pin: GPIO16
  mdio_pin: GPIO17
  clk:
    pin: GPIO0
    mode: CLK_EXT_IN
  phy_addr: 0

logger:
api:
ota:
  platform: esphome

spi:
  clk_pin: GPIO14
  mosi_pin: GPIO13
  miso_pin: GPIO12

cc1101:
  id: my_cc1101
  cs_pin: GPIO15
  frequency: 433.92MHz
  # Quieter receiver: a lower gain target and a higher OOK decision threshold
  # keep idle noise from filling the receive buffer.
  magn_target: 33dB
  filter_length_ask_ook: 12dB

remote_transmitter:
  id: rf_tx
  pin: GPIO4 # GDO0
  carrier_duty_percent: 100%
  on_transmit:
    then:
      - cc1101.begin_tx
  on_complete:
    then:
      - cc1101.begin_rx

remote_receiver:
  id: rf_rx
  pin: GPIO5 # GDO2
  filter: 200us
  idle: 15ms
  filter_symbols: 20 # drop tiny noise bursts before they take a buffer slot
  buffer_size: 16kb

radio_frequency:
  - platform: ir_rf_proxy
    name: RF Transmitter
    frequency: 433.92MHz
    remote_transmitter_id: rf_tx
  - platform: ir_rf_proxy
    name: RF Receiver
    frequency: 433.92MHz
    remote_receiver_id: rf_rx
```

## Example: a second radio on the same node (303.87 MHz)

A node can carry one CC1101 per frequency. The modules share the SPI bus (SCK, MOSI, MISO), and each has its own CSN, GDO0 and GDO2 pins. This adds a 303.87 MHz CC1101 to the wESP32 above. The second CSN takes GPIO5, so the first CC1101's GDO2 moves from GPIO5 to GPIO36:

| | ESP32 |
| --- | --- |
| SCK, MOSI, MISO (both CC1101s) | Shared: GPIO14, GPIO13, GPIO12 |
| First CC1101's GDO2 (receive) | GPIO36, moved from GPIO5 |
| Second CC1101's CSN | GPIO5 |
| Second CC1101's GDO0 (transmit) | GPIO33 |
| Second CC1101's GDO2 (receive) | GPIO35 |

Input-only pins (GPIO34 to GPIO39) are fine for receive. ESPHome logs `gpio_pullup_en ... input-only pad has no internal PU` for them at boot, which is harmless: GDO2 drives the line.

Replace the `cc1101`, `remote_transmitter`, `remote_receiver` and `radio_frequency` sections with:

```yaml
cc1101:
  - id: cc1101_433
    cs_pin: GPIO15
    frequency: 433.92MHz
    magn_target: 33dB
    filter_length_ask_ook: 12dB
  - id: cc1101_303
    cs_pin: GPIO5
    frequency: 303.87MHz
    magn_target: 33dB
    filter_length_ask_ook: 12dB

remote_transmitter:
  - id: rf_tx_433
    pin: GPIO4 # GDO0 of the 433.92 MHz CC1101
    carrier_duty_percent: 100%
    on_transmit:
      then:
        - cc1101.begin_tx: cc1101_433
    on_complete:
      then:
        - cc1101.begin_rx: cc1101_433
  - id: rf_tx_303
    pin: GPIO33 # GDO0 of the 303.87 MHz CC1101
    carrier_duty_percent: 100%
    on_transmit:
      then:
        - cc1101.begin_tx: cc1101_303
    on_complete:
      then:
        - cc1101.begin_rx: cc1101_303

remote_receiver:
  - id: rf_rx_433
    pin: GPIO36 # GDO2 of the 433.92 MHz CC1101
    filter: 200us
    idle: 15ms
    filter_symbols: 20
    buffer_size: 16kb
  - id: rf_rx_303
    pin: GPIO35 # GDO2 of the 303.87 MHz CC1101
    filter: 200us
    idle: 15ms
    filter_symbols: 20
    buffer_size: 16kb

radio_frequency:
  - platform: ir_rf_proxy
    name: RF Transmitter 433
    frequency: 433.92MHz
    remote_transmitter_id: rf_tx_433
  - platform: ir_rf_proxy
    name: RF Receiver 433
    frequency: 433.92MHz
    remote_receiver_id: rf_rx_433
  - platform: ir_rf_proxy
    name: RF Transmitter 303
    frequency: 303.87MHz
    remote_transmitter_id: rf_tx_303
  - platform: ir_rf_proxy
    name: RF Receiver 303
    frequency: 303.87MHz
    remote_receiver_id: rf_rx_303
```

Clicker shows these as two radios, one per frequency.

- **Name the CC1101 in every `cc1101.begin_tx` and `cc1101.begin_rx`.** With more than one, ESPHome can't pick one for you.
- **Use a module made for the band.** CC1101 modules are tuned for one band by their matching components and antenna: for 303.87 MHz use one sold for 315 MHz. A 433 MHz module set to 303.87 MHz receives poorly.
- **Keep the antennas a few centimetres apart.** A transmission on one radio can briefly deafen a receiver right next to it.
- **Mind the ESP32's RMT memory.** On a classic ESP32, two radios at the default `rmt_symbols` (192 per receiver, 64 per transmitter) use all 512 symbols. More radios need smaller `rmt_symbols`. An ESP32-S3 has only 192 receive symbols in all, so with more than one receiver set `rmt_symbols: 48` on each.

## Things that matter

- **Don't set `gdo0_pin` on the `cc1101`** when GDO0 is also the `remote_transmitter` pin. It takes the pin away from the transmitter, and sending silently stops working.
- **Switch the CC1101 between transmit and receive** with `cc1101.begin_tx` and `cc1101.begin_rx` around each transmission, as above. The CC1101 is half duplex, so the node doesn't hear its own transmissions.
- **Keep the receiver from drowning in noise.** With the defaults, a CC1101 hears so much background noise that the receiver reports "Buffer overflow" and real presses get lost. The `magn_target`, `filter_length_ask_ook`, `filter_symbols` and `buffer_size` settings above fixed that. If Live signals still shows a constant stream of short undecoded bursts, try `filter_length_ask_ook: 16dB`.
- **Leave `dump` off, or limit it to `rc_switch`.** `dump: raw` with the ESPHome logs open makes the receiver stall for about 150–200 ms per press. Clicker gets the timings over the API either way.
- **One frequency per CC1101.** For a second band, add a second CC1101 module, on the same node (see above) or on another node, with its own `remote_transmitter`, `remote_receiver` and `ir_rf_proxy` pair at that frequency. Clicker keeps each band's devices on its own radio.
- **If a receiver that used to work hears only garbage**, reboot the node. A CC1101 can occasionally end up in a bad state that a restart clears.

## Checking it works

1. In Home Assistant, the node's device page shows an **RF Transmitter** entity.
2. In the Clicker panel, the **Radios** tab shows the node's radio as **Online**, at its frequency, with **Sends** and **Receives**.
3. On the **Live signals** tab, press a button on any remote near the node. A reception should appear within a second.

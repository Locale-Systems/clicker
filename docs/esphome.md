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

## Things that matter

- **Don't set `gdo0_pin` on the `cc1101`** when GDO0 is also the `remote_transmitter` pin. It takes the pin away from the transmitter, and sending silently stops working.
- **Switch the CC1101 between transmit and receive** with `cc1101.begin_tx` and `cc1101.begin_rx` around each transmission, as above. The CC1101 is half duplex, so the node doesn't hear its own transmissions.
- **Keep the receiver from drowning in noise.** With the defaults, a CC1101 hears so much background noise that the receiver reports "Buffer overflow" and real presses get lost. The `magn_target`, `filter_length_ask_ook`, `filter_symbols` and `buffer_size` settings above fixed that. If Live signals still shows a constant stream of short undecoded bursts, try `filter_length_ask_ook: 16dB`.
- **Leave `dump` off, or limit it to `rc_switch`.** `dump: raw` with the ESPHome logs open makes the receiver stall for about 150–200 ms per press. Clicker gets the timings over the API either way.
- **One frequency per CC1101.** For a second band (for example 303.87 MHz fans), add a second CC1101 module, on the same node with its own CS, GDO0 and GDO2 pins, or on another node, with its own `remote_transmitter`, `remote_receiver` and `ir_rf_proxy` pair at that frequency. Clicker keeps each band's devices on its own radio.
- **If a receiver that used to work hears only garbage**, reboot the node. A CC1101 can occasionally end up in a bad state that a restart clears.

## Checking it works

1. In Home Assistant, the node's device page shows an **RF Transmitter** entity.
2. In the Clicker panel, the **Radios** tab shows the node's radio as **Online**, at its frequency, with **Sends** and **Receives**.
3. On the **Live signals** tab, press a button on any remote near the node. A reception should appear within a second.

# Shure Wireless for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Tests](https://github.com/brianegge/homeassistant-shure-wireless/actions/workflows/tests.yml/badge.svg)](https://github.com/brianegge/homeassistant-shure-wireless/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Home Assistant custom integration for monitoring Shure wireless microphone receivers over their network control protocol. Supports real-time push updates for battery levels, RF signal strength, audio levels, and transmitter status.

## Supported Devices

Shure wireless receivers with network control capability, including:

- **SLXD4** / **SLXD4D** – SLX-D single and dual-channel receivers
- **ULXD4** / **ULXD4D** / **ULXD4Q** – ULX-D single, dual, and quad-channel receivers
- **QLXD4** – QLX-D single-channel receivers
- **AD4D** / **AD4Q** – Axient Digital dual and quad-channel receivers
- **AXT400** – Axient single-channel receivers

Any Shure receiver that supports the Shure Network Control Protocol over TCP port 2202 should work.

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click the three-dot menu → **Custom repositories**
3. Add `https://github.com/brianegge/homeassistant-shure-wireless` with category **Integration**
4. Search for "Shure Wireless" and install
5. Restart Home Assistant

### Manual

1. Copy `custom_components/shure_wireless` to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

### Automatic Discovery (Zeroconf)

If your Shure receiver supports mDNS/Zeroconf (service type `_shure._tcp.local.`), Home Assistant will automatically discover it. You'll be prompted to confirm and select the number of channels.

### Manual Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Shure Wireless"
3. Enter your receiver's details:
   - **Host**: Hostname or IP address of the receiver
   - **Port**: Network control port (default: 2202)
   - **Number of channels**: 1, 2, or 4 (must match your receiver model)

### Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| Host | Hostname or IP address of the Shure receiver | *(required)* |
| Port | TCP port for the Shure Network Control Protocol | 2202 |
| Number of channels | Number of wireless channels on the receiver (1, 2, or 4) | 4 |

To update these settings after initial setup, use the **Reconfigure** option in the integration's settings.

## Sensors

For each wireless channel, the following sensors are created:

| Sensor | Unit | Description |
|--------|------|-------------|
| Battery | % | Transmitter battery charge percentage |
| Battery runtime | min | Estimated remaining battery runtime |
| RF signal | dBm | RF signal strength from the transmitter |
| Audio level | dBFS | Current audio input level (disabled by default) |
| Channel name | — | The configured channel/transmitter name |

### Sensor Attributes

**Battery sensor:**
- `battery_bars` – Battery level in bars (0–5)
- `battery_type` – Battery chemistry (e.g., LITHIUM_ION, AA)
- `battery_health` – Battery health percentage
- `battery_cycle_count` – Charge cycle count
- `battery_temperature_c` – Battery temperature in °C

**RF signal sensor:**
- `frequency` – Operating frequency in MHz
- `interference_status` – RF interference detection status
- `encryption_status` – Wireless encryption status

**Audio level sensor:**
- `peak_level` – Peak audio level
- `gain` – Audio gain setting
- `mute` – Receiver mute status
- `tx_mute` – Transmitter mute status

**Channel name sensor:**
- `tx_model` – Transmitter model
- `tx_device_id` – Transmitter device identifier

## Removal

To remove the integration:

1. Go to **Settings** → **Devices & Services**
2. Find the Shure Wireless integration
3. Click the three-dot menu → **Delete**

This removes the config entry and all associated entities and devices.

## Technical Details

- **IoT Class**: Local Push — the receiver pushes real-time updates over TCP
- **Protocol**: Shure Network Control Protocol over TCP (port 2202)
- **Update Method**: Push updates via persistent TCP connection with 60-second heartbeat
- **Connection**: Automatic reconnection with logging on connection state changes

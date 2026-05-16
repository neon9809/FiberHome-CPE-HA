# FiberHome-CPE-HA

`FiberHome-CPE-HA` is a custom integration for Home Assistant that connects to Fiberhome 5G CPE devices, synchronizing device status, network signal, traffic statistics, and the latest SMS as Home Assistant sensors.

## Features

- Automatically logs into the CPE and retrieves basic device information
- Exposes system status sensors such as temperature, CPU, memory, and uptime
- Exposes signal sensors such as RSRP, RSSI, SINR, RSRQ, BAND, and PCI
- Exposes today's and this month's upload/download traffic sensors
- Optionally enables SMS-related entities: `Latest Message`, `Unread SMS`, and `New SMS`
- Does not automatically mark SMS messages as read (avoids side effects on the device)
- Provides IMEI/IMSI diagnostic sensors (disabled by default)

## Configuration

When adding the integration in Home Assistant, the following fields need to be filled in:

- Host (IP Address)
- Username
- Password
- Refresh Interval
- Enable SMS entities

The default refresh interval is `60` seconds, with a configurable range from `1` to `21600` seconds.

## Installation

### Install via HACS (recommended)

1. In Home Assistant, open `HACS`
2. Click the menu in the top right and select `Custom repositories`
3. Add the repository URL: `https://github.com/neon9809/FiberHome-CPE-HA`
4. Select the category: `integration`
5. After adding, go to `HACS -> Integrations`
6. Search for `Fiberhome CPE` and install it

### Manual installation

1. Copy the `custom_components/fiberhome_cpe` directory to the `custom_components` directory within your Home Assistant configuration directory
2. The final path should be `config/custom_components/fiberhome_cpe/`
3. Restart Home Assistant
4. Navigate to "Settings -> Devices & Services -> Add Integration"
5. Search for `Fiberhome CPE`

## Data Source

This project references the `obtainData.py` file in the repository, using the same session acquisition, AES encryption/decryption, and API request methods to access the CPE.

SMS reading logic references:

- [fiberhome-cpe-sms](https://gitee.com/upchr/fiberhome-cpe-sms)
- [fiberhome-cpe](https://github.com/kukume/fiberhome-cpe)

## Credit

- Project Homepage: [neon9809](https://github.com/neon9809)

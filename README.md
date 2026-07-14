# Clockify Time Tracking for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/your-username/ha-clockify)](https://github.com/your-username/ha-clockify/releases)
[![License](https://img.shields.io/github/license/your-username/ha-clockify)](LICENSE)

A Home Assistant custom integration for [Clockify](https://clockify.me) time tracking. Monitor your current tracking status and control time entries directly from Home Assistant.

## Features

- **Real-time status** — see whether you're currently tracking time or idle
- **Current entry details** — project name, description, and elapsed duration
- **Start tracking** — begin a new time entry with optional project and description
- **Stop tracking** — stop the currently running entry
- **Resume recent entries** — restart any of your last 10 time entries with one call

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**
3. Add this repository URL with category **Integration**
4. Click **Install**
5. Restart Home Assistant

### Manual

1. Download the latest release from the [Releases](https://github.com/your-username/ha-clockify/releases) page
2. Extract and copy the `custom_components/clockify` folder into your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **Clockify**
3. Enter your Clockify API key
4. Select your workspace (automatic if you only have one)

### Getting your API key

Navigate to your [Clockify Profile Settings](https://app.clockify.me/user/preferences#advanced), scroll to the **API** section, and generate or copy your key.

## Entities

| Entity | Description |
|--------|-------------|
| `sensor.clockify_status` | `tracking` or `idle` |
| `sensor.clockify_current_project` | Name of the active project |
| `sensor.clockify_current_duration` | Elapsed time (HH:MM:SS) |
| `sensor.clockify_current_description` | Description of the running entry |

All sensors include additional attributes with raw entry data.

## Services

### `clockify.start_tracking`

Start a new time entry.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `project_id` | No | Clockify project ID |
| `description` | No | Entry description |
| `billable` | No | Whether the entry is billable (default: `false`) |

### `clockify.stop_tracking`

Stop the currently running time entry. No parameters.

### `clockify.resume_entry`

Resume a recent time entry (creates a new entry with the same project, description, and tags).

| Parameter | Required | Description |
|-----------|----------|-------------|
| `entry_index` | Yes | Index of the recent entry to resume (1 = most recent, up to 10) |

## Automation Example

```yaml
automation:
  - alias: "Start tracking when I arrive at the office"
    trigger:
      - platform: zone
        entity_id: person.me
        zone: zone.office
        event: enter
    action:
      - service: clockify.start_tracking
        data:
          project_id: "64a1b2c3d4e5f6..."
          description: "Office hours"
```

## API Rate Limits

The integration polls the Clockify API every 60 seconds. Clockify's free plan allows up to 50 requests per second, so this is well within limits. After calling a service (start/stop/resume), sensors refresh immediately without waiting for the next polling cycle.

## Development & Testing

### Docker

```bash
docker run -d \
  --name ha-dev \
  -p 8123:8123 \
  -v $(pwd)/custom_components:/config/custom_components \
  ghcr.io/home-assistant/home-assistant:stable
```

Open `http://localhost:8123`, complete onboarding, then add the Clockify integration.

### Home Assistant Core dev environment

```bash
git clone https://github.com/home-assistant/core.git
cd core
script/setup
ln -s /path/to/ha-clockify/custom_components/clockify homeassistant/components/clockify
hass -c config
```

## Contributing

Contributions are welcome! Please open an issue or pull request.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

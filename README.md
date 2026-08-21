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

All data comes from one `DataUpdateCoordinator` that polls Clockify every 60 seconds and fetches the running entry, recent entries, today/yesterday/week entries, projects, tasks (for whichever project is currently selected), and clients in one pass. Several sensors also depend on the `select.*` entities below — picking a value there changes what a sensor reports, without needing a new poll for most of them.

### Selects (filters used by the sensors below)

| Entity | Sets |
|--------|------|
| `select.project` | `project_id` fallback for `start_tracking`, and scopes `select.task`'s options |
| `select.work_project` / `select.personal_project` | the project used by "Work" / "Personal" layer sensors |
| `select.task` | `task_id` fallback for `start_tracking` |
| `select.work_client` / `select.personal_client` | the client used by "Work Client" / "Personal Client" sensors |
| `select.recent_entry` | `entry_index` fallback for `resume_entry` |

### Tracking sensors (current running entry)

| Entity | Reports |
|--------|---------|
| `sensor.tracking_status` | `tracking` or `idle` |
| `sensor.tracking_project` | Project name of the running entry |
| `sensor.tracking_client` | Client name of the running entry's project |
| `sensor.tracking_task` | Task name of the running entry |
| `sensor.tracking_description` | Description of the running entry |
| `sensor.tracking_start_time` | Start timestamp of the running entry |

### Recent entries

| Entity | Reports |
|--------|---------|
| `sensor.recent_entries` | Count of your last 10 entries; full list (description, project, task, duration, billable, tags) in attributes |

### Today / Yesterday / Week statistics

Each period has the same 4-layer × 2-measure grid: entry count (+ list) and duration, each filterable by **work project**, **personal project**, the general **project** select, or **overall** (unfiltered). A layer with nothing selected in its corresponding select reports zero/empty — it never silently falls back to "all entries". Yesterday's duration excludes any still-open entry (it's really still running today); Today's and Week's duration count it up to now.

| Layer | Entries sensor | Duration sensor |
|-------|-----------------|------------------|
| Overall | `sensor.today_entries` | `sensor.today_duration` |
| Work project | `sensor.today_work_project_entries` | `sensor.today_work_project_duration` |
| Personal project | `sensor.today_personal_project_entries` | `sensor.today_personal_project_duration` |
| Project (general select) | `sensor.today_project_entries` | `sensor.today_project_duration` |

Same pattern with `yesterday_*` and `week_*` in place of `today_*` (24 sensors total across the three periods).

### Client-level statistics

Client sensors aggregate across **every project belonging to that client**, not just one project (a Clockify client can have many projects). Same period coverage as the project grid above (Today/Yesterday/Week × entries/duration), but only 2 layers — **overall** and the general **project** select don't apply to a client filter the same way:

| Layer | Entries sensor | Duration sensor |
|-------|-----------------|------------------|
| Work client | `sensor.today_work_client_entries` | `sensor.today_work_client_duration` |
| Personal client | `sensor.today_personal_client_entries` | `sensor.today_personal_client_duration` |

Same pattern with `yesterday_*_client_*` and `week_*_client_*` (12 sensors total across the three periods).

All sensors include additional attributes with raw entry data (project/client/task names and IDs, billable status, tag IDs, per-entry lists, etc.).

## Services

### `clockify.start_tracking`

Start a new time entry.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `project_id` | No | Clockify project ID. Falls back to `select.project` if omitted |
| `task_id` | No | Clockify task ID. Falls back to `select.task` if omitted |
| `description` | No | Entry description |
| `billable` | No | Whether the entry is billable (default: `false`) |

### `clockify.stop_tracking`

Stop the currently running time entry. No parameters.

### `clockify.resume_entry`

Resume a recent time entry (creates a new entry with the same project, task, description, and tags).

| Parameter | Required | Description |
|-----------|----------|-------------|
| `entry_index` | No | Index of the recent entry to resume (1 = most recent, up to 10). Falls back to `select.recent_entry` if omitted |

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

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant custom integration (`custom_components/clockify`) that connects to the Clockify time-tracking API. It's a HACS-installable component, not a standalone app — it only makes sense running inside a Home Assistant instance.

## Commands

Run tests:
```bash
pytest
```

Run a single test:
```bash
pytest tests/test_api.py::test_start_entry
```

Run the integration inside a real Home Assistant dev instance (creates `.venv` and a `config/` dir with the integration symlinked in on first run):
```bash
./scripts/develop
```
Then open http://localhost:8123, complete onboarding, and add the Clockify integration via Settings > Devices & Services.

There is no lint/format command configured in this repo.

## Architecture

Standard Home Assistant integration structure, all under `custom_components/clockify/`:

- **`api.py`** — `ClockifyApiClient`: thin async wrapper over the Clockify REST API (`https://api.clockify.me/api/v1`) using an injected `aiohttp.ClientSession`. All HTTP calls funnel through `_request()`. This is the only file that talks to Clockify directly.
- **`coordinator.py`** — `ClockifyDataUpdateCoordinator` (a `DataUpdateCoordinator`): polls every 60s (`DEFAULT_SCAN_INTERVAL`) and fetches running entry, recent entries, today/yesterday/week entries, and the project list in one `_async_update_data()` pass, building a `projects_map` (id → name) that entities use to resolve project names. It also holds mutable, non-persisted UI selection state (`selected_project_id`, `work_project_id`, `personal_project_id`, `selected_recent_index`) that the `select` platform writes into and both `sensor` entities and `__init__.py` service handlers read back out. This is the shared state hub — sensors and selects don't talk to each other directly, they go through the coordinator.
- **`sensor.py`** — read-only entities, all subclassing `ClockifyBaseSensor` (a `CoordinatorEntity`). Several duration sensors filter `today`/`week` entries by `coordinator.work_project_id` / `personal_project_id` (set via the corresponding select entities) to split tracked time into "work" vs "personal" buckets. Duration formatting/summing logic is duplicated per sensor class rather than shared — follow the existing pattern when adding a new one rather than introducing a shared mixin, unless doing a deliberate refactor.
- **`select.py`** — `SelectEntity` platforms that let the user pick a project (general/work/personal) or a recent entry from a dropdown; picking an option writes into the coordinator's mutable state described above, which is what `service.yaml`-defined services and filtered sensors then use as a fallback/filter.
- **`__init__.py`** — sets up the coordinator on `async_setup_entry`, forwards to the `sensor`/`select` platforms, and registers the three domain services (`start_tracking`, `stop_tracking`, `resume_entry`) declared in `services.yaml`. Service handlers grab "the" coordinator via `hass.data[DOMAIN]` (first value — this integration assumes a single configured entry) and fall back to coordinator selection state (`selected_project_id`, `selected_recent_index`) when the service call doesn't pass explicit parameters.
- **`config_flow.py`** — UI setup flow: takes an API key, calls `get_user`/`get_workspaces` to validate it, and either auto-selects the sole workspace or prompts the user to pick one among several.
- **`const.py`** — domain string, API base URL, poll interval, and recent-entries limit (10).

## Testing

`tests/test_api.py` mocks `aiohttp.ClientSession.request` directly (via `MagicMock`/`AsyncMock` context managers) rather than using `aioresponses` or HA's test harness — follow that pattern for new API client tests. There is no test coverage yet for `coordinator.py`, `sensor.py`, `select.py`, or `config_flow.py`.

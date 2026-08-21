import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ClockifyApiClient
from .const import DOMAIN
from .coordinator import ClockifyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    client = ClockifyApiClient(session, entry.data["api_key"])
    coordinator = ClockifyDataUpdateCoordinator(
        hass, client, entry.data["workspace_id"], entry.data["user_id"]
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


def _register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "start_tracking"):
        return

    async def _get_coordinator(call: ServiceCall) -> ClockifyDataUpdateCoordinator:
        coordinators = list(hass.data[DOMAIN].values())
        if not coordinators:
            raise ValueError("No Clockify integration configured")
        return coordinators[0]

    def _resolve_project_id(
        call: ServiceCall, coordinator: ClockifyDataUpdateCoordinator
    ) -> str | None:
        project_id = call.data.get("project_id")
        if project_id:
            return project_id
        return getattr(coordinator, "selected_project_id", None)

    def _resolve_task_id(
        call: ServiceCall, coordinator: ClockifyDataUpdateCoordinator
    ) -> str | None:
        task_id = call.data.get("task_id")
        if task_id:
            return task_id
        selected = getattr(coordinator, "selected_task_id", None)
        if selected and coordinator.data and selected in coordinator.data.get("tasks", {}):
            return selected
        return None

    async def handle_start_tracking(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call)
        project_id = _resolve_project_id(call, coordinator)
        task_id = _resolve_task_id(call, coordinator)
        await coordinator.client.start_entry(
            workspace_id=coordinator.workspace_id,
            project_id=project_id,
            description=call.data.get("description", ""),
            billable=call.data.get("billable", False),
            task_id=task_id,
        )
        await coordinator.async_request_refresh()

    async def handle_stop_tracking(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call)
        await coordinator.client.stop_entry(
            coordinator.workspace_id, coordinator.user_id
        )
        await coordinator.async_request_refresh()

    async def handle_resume_entry(call: ServiceCall) -> None:
        coordinator = await _get_coordinator(call)
        entry_index = call.data.get("entry_index")
        if entry_index is not None:
            index = entry_index - 1
        elif coordinator.selected_recent_index is not None:
            index = coordinator.selected_recent_index
        else:
            raise ValueError(
                "No entry_index provided and no recent entry selected"
            )
        recent = coordinator.data.get("recent", [])
        if index >= len(recent):
            raise ValueError(
                f"Entry index {index + 1} out of range "
                f"(only {len(recent)} recent entries available)"
            )
        entry = recent[index]
        await coordinator.client.start_entry(
            workspace_id=coordinator.workspace_id,
            project_id=entry.get("projectId"),
            description=entry.get("description", ""),
            billable=entry.get("billable", False),
            tag_ids=entry.get("tagIds"),
            task_id=entry.get("taskId"),
        )
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        "start_tracking",
        handle_start_tracking,
        schema=vol.Schema(
            {
                vol.Optional("project_id"): str,
                vol.Optional("description", default=""): str,
                vol.Optional("billable", default=False): bool,
                vol.Optional("task_id"): str,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        "stop_tracking",
        handle_stop_tracking,
        schema=vol.Schema({}),
    )

    hass.services.async_register(
        DOMAIN,
        "resume_entry",
        handle_resume_entry,
        schema=vol.Schema({vol.Optional("entry_index"): vol.All(int, vol.Range(1, 10))}),
    )

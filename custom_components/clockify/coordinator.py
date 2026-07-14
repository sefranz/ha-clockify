from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ClockifyApiClient
from .const import DEFAULT_SCAN_INTERVAL, RECENT_ENTRIES_LIMIT

_LOGGER = logging.getLogger(__name__)


class ClockifyDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        client: ClockifyApiClient,
        workspace_id: str,
        user_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Clockify",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.workspace_id = workspace_id
        self.user_id = user_id

    async def _async_update_data(self) -> dict:
        try:
            running = await self.client.get_running_entry(
                self.workspace_id, self.user_id
            )
            recent = await self.client.get_recent_entries(
                self.workspace_id, self.user_id, RECENT_ENTRIES_LIMIT
            )
            projects = await self.client.get_projects(self.workspace_id)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Clockify API: {err}") from err

        projects_map = {p["id"]: p["name"] for p in projects}

        return {
            "running": running,
            "recent": recent,
            "projects": projects_map,
        }

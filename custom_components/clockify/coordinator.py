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
        self.selected_project_id: str | None = None
        self.work_project_id: str | None = None
        self.personal_project_id: str | None = None
        self.selected_recent_index: int | None = None
        self.selected_task_id: str | None = None
        self.work_client_id: str | None = None
        self.personal_client_id: str | None = None

    async def _async_update_data(self) -> dict:
        try:
            running = await self.client.get_running_entry(
                self.workspace_id, self.user_id
            )
            recent = await self.client.get_recent_entries(
                self.workspace_id, self.user_id, RECENT_ENTRIES_LIMIT
            )
            today = await self.client.get_today_entries(
                self.workspace_id, self.user_id
            )
            yesterday = await self.client.get_yesterday_entries(
                self.workspace_id, self.user_id
            )
            week = await self.client.get_week_entries(
                self.workspace_id, self.user_id
            )
            projects = await self.client.get_projects(self.workspace_id)
            tasks = (
                await self.client.get_tasks(self.workspace_id, self.selected_project_id)
                if self.selected_project_id
                else []
            )
            clients = await self.client.get_clients(self.workspace_id)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Clockify API: {err}") from err

        clients_map = {c["id"]: c["name"] for c in clients}
        projects_map = {p["id"]: p["name"] for p in projects}
        project_details = {
            p["id"]: {
                "client_id": p.get("clientId"),
                "client_name": clients_map.get(p.get("clientId")),
                "color": p.get("color"),
                "billable": p.get("billable", False),
                "archived": p.get("archived", False),
            }
            for p in projects
        }
        tasks_map = {t["id"]: t["name"] for t in tasks}

        return {
            "running": running,
            "recent": recent,
            "today": today,
            "yesterday": yesterday,
            "week": week,
            "projects": projects_map,
            "project_details": project_details,
            "tasks": tasks_map,
            "clients": clients_map,
        }

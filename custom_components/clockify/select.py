from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ClockifyDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ClockifyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ClockifyProjectSelect(coordinator, entry),
        ClockifyWorkProjectSelect(coordinator, entry),
        ClockifyPersonalProjectSelect(coordinator, entry),
        ClockifyRecentEntrySelect(coordinator, entry),
    ])


class ClockifyProjectSelect(CoordinatorEntity, SelectEntity):
    def __init__(
        self, coordinator: ClockifyDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_project_select"
        self._attr_has_entity_name = True
        self._attr_name = "Project"
        self._attr_icon = "mdi:folder-outline"
        self._selected_project_id: str | None = None

    @property
    def options(self) -> list[str]:
        if not self.coordinator.data:
            return []
        projects = self.coordinator.data.get("projects", {})
        return list(projects.values())

    @property
    def current_option(self) -> str | None:
        if not self._selected_project_id or not self.coordinator.data:
            return None
        projects = self.coordinator.data.get("projects", {})
        return projects.get(self._selected_project_id)

    async def async_select_option(self, option: str) -> None:
        projects = self.coordinator.data.get("projects", {})
        for project_id, name in projects.items():
            if name == option:
                self._selected_project_id = project_id
                self.coordinator.selected_project_id = project_id
                break
        self.async_write_ha_state()


class ClockifyWorkProjectSelect(CoordinatorEntity, SelectEntity):
    def __init__(
        self, coordinator: ClockifyDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_work_project_select"
        self._attr_has_entity_name = True
        self._attr_name = "Work Project"
        self._attr_icon = "mdi:briefcase-outline"
        self._selected_project_id: str | None = None

    @property
    def options(self) -> list[str]:
        if not self.coordinator.data:
            return []
        projects = self.coordinator.data.get("projects", {})
        return list(projects.values())

    @property
    def current_option(self) -> str | None:
        if not self._selected_project_id or not self.coordinator.data:
            return None
        projects = self.coordinator.data.get("projects", {})
        return projects.get(self._selected_project_id)

    async def async_select_option(self, option: str) -> None:
        projects = self.coordinator.data.get("projects", {})
        for project_id, name in projects.items():
            if name == option:
                self._selected_project_id = project_id
                self.coordinator.work_project_id = project_id
                break
        self.async_write_ha_state()


class ClockifyPersonalProjectSelect(CoordinatorEntity, SelectEntity):
    def __init__(
        self, coordinator: ClockifyDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_personal_project_select"
        self._attr_has_entity_name = True
        self._attr_name = "Personal Project"
        self._attr_icon = "mdi:account-outline"
        self._selected_project_id: str | None = None

    @property
    def options(self) -> list[str]:
        if not self.coordinator.data:
            return []
        projects = self.coordinator.data.get("projects", {})
        return list(projects.values())

    @property
    def current_option(self) -> str | None:
        if not self._selected_project_id or not self.coordinator.data:
            return None
        projects = self.coordinator.data.get("projects", {})
        return projects.get(self._selected_project_id)

    async def async_select_option(self, option: str) -> None:
        projects = self.coordinator.data.get("projects", {})
        for project_id, name in projects.items():
            if name == option:
                self._selected_project_id = project_id
                self.coordinator.personal_project_id = project_id
                break
        self.async_write_ha_state()


class ClockifyRecentEntrySelect(CoordinatorEntity, SelectEntity):
    def __init__(
        self, coordinator: ClockifyDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_recent_entry_select"
        self._attr_has_entity_name = True
        self._attr_name = "Recent Entry"
        self._attr_icon = "mdi:history"
        self._selected_index: int | None = None

    def _entry_label(self, entry: dict, index: int) -> str:
        description = entry.get("description") or "No description"
        project_id = entry.get("projectId")
        projects = self.coordinator.data.get("projects", {})
        project_name = projects.get(project_id, "") if project_id else ""
        if project_name:
            return f"{project_name} — {description}"
        return description

    @property
    def _recent_entries(self) -> list[dict]:
        if not self.coordinator.data:
            return []
        return self.coordinator.data.get("recent", [])

    @property
    def options(self) -> list[str]:
        return [
            self._entry_label(entry, i)
            for i, entry in enumerate(self._recent_entries)
        ]

    @property
    def current_option(self) -> str | None:
        entries = self._recent_entries
        if self._selected_index is None or self._selected_index >= len(entries):
            return None
        return self._entry_label(entries[self._selected_index], self._selected_index)

    async def async_select_option(self, option: str) -> None:
        for i, entry in enumerate(self._recent_entries):
            if self._entry_label(entry, i) == option:
                self._selected_index = i
                self.coordinator.selected_recent_index = i
                break
        self.async_write_ha_state()

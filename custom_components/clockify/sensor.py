from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity
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
    async_add_entities(
        [
            ClockifyStatusSensor(coordinator, entry),
            ClockifyProjectSensor(coordinator, entry),
            ClockifyDurationSensor(coordinator, entry),
            ClockifyDescriptionSensor(coordinator, entry),
        ]
    )


class ClockifyBaseSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator: ClockifyDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_has_entity_name = True
        self._attr_name = name

    @property
    def _running_entry(self) -> dict | None:
        return self.coordinator.data.get("running") if self.coordinator.data else None


class ClockifyStatusSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "status", "Status")
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> str:
        return "tracking" if self._running_entry else "idle"

    @property
    def extra_state_attributes(self) -> dict:
        if not self._running_entry:
            return {}
        return {"entry_id": self._running_entry.get("id")}


class ClockifyProjectSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "project", "Current Project")
        self._attr_icon = "mdi:folder-outline"

    @property
    def native_value(self) -> str | None:
        entry = self._running_entry
        if not entry:
            return None
        project_id = entry.get("projectId")
        if not project_id:
            return "No project"
        projects = self.coordinator.data.get("projects", {})
        return projects.get(project_id, "Unknown")


class ClockifyDurationSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "duration", "Current Duration")
        self._attr_icon = "mdi:timer-outline"

    @property
    def native_value(self) -> str | None:
        entry = self._running_entry
        if not entry:
            return None
        start_str = entry.get("timeInterval", {}).get("start")
        if not start_str:
            return None
        start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        elapsed = datetime.now(timezone.utc) - start
        total_seconds = int(elapsed.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def extra_state_attributes(self) -> dict:
        entry = self._running_entry
        if not entry:
            return {}
        return {"start_time": entry.get("timeInterval", {}).get("start")}


class ClockifyDescriptionSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "description", "Current Description")
        self._attr_icon = "mdi:text"

    @property
    def native_value(self) -> str | None:
        entry = self._running_entry
        if not entry:
            return None
        return entry.get("description") or "No description"

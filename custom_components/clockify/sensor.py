from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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
            ClockifyStartTimeSensor(coordinator, entry),
            ClockifyDescriptionSensor(coordinator, entry),
            ClockifyTaskSensor(coordinator, entry),
            ClockifyRecentEntriesSensor(coordinator, entry),
            ClockifyTodayEntriesSensor(coordinator, entry),
            ClockifyYesterdayEntriesSensor(coordinator, entry),
            ClockifyTodayDurationSensor(coordinator, entry),
            ClockifyYesterdayDurationSensor(coordinator, entry),
            ClockifyTodayWorkDurationSensor(coordinator, entry),
            ClockifyTodayPersonalDurationSensor(coordinator, entry),
            ClockifyWeekWorkEntriesSensor(coordinator, entry),
            ClockifyWeekWorkDurationSensor(coordinator, entry),
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
        super().__init__(coordinator, entry, "status", "Tracking: Status")
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
        super().__init__(coordinator, entry, "project", "Tracking: Project")
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

    @property
    def extra_state_attributes(self) -> dict:
        entry = self._running_entry
        if not entry:
            return {}
        return {"project_id": entry.get("projectId")}


class ClockifyStartTimeSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "start_time", "Tracking: Start Time")
        self._attr_icon = "mdi:clock-start"
        self._attr_device_class = "timestamp"

    @property
    def native_value(self) -> datetime | None:
        entry = self._running_entry
        if not entry:
            return None
        start_str = entry.get("timeInterval", {}).get("start")
        if not start_str:
            return None
        return datetime.fromisoformat(start_str.replace("Z", "+00:00"))


class ClockifyDescriptionSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "description", "Tracking: Description")
        self._attr_icon = "mdi:text"

    @property
    def native_value(self) -> str | None:
        entry = self._running_entry
        if not entry:
            return None
        return entry.get("description") or "No description"


class ClockifyTaskSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "task", "Tracking: Task")
        self._attr_icon = "mdi:checkbox-marked-outline"

    @property
    def native_value(self) -> str | None:
        entry = self._running_entry
        if not entry:
            return None
        task = entry.get("task")
        if not task:
            return "No task"
        return task.get("name", "Unknown")

    @property
    def extra_state_attributes(self) -> dict:
        entry = self._running_entry
        if not entry:
            return {}
        return {"task_id": entry.get("taskId")}


class ClockifyRecentEntriesSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "recent_entries", "Recent Entries")
        self._attr_icon = "mdi:history"

    def _format_duration(self, entry: dict) -> str:
        interval = entry.get("timeInterval", {})
        start_str = interval.get("start")
        end_str = interval.get("end")
        if not start_str or not end_str:
            return "in progress"
        start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        total_seconds = int((end - start).total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    @property
    def native_value(self) -> int | None:
        if not self.coordinator.data:
            return None
        recent = self.coordinator.data.get("recent", [])
        return len(recent)

    @property
    def extra_state_attributes(self) -> dict:
        if not self.coordinator.data:
            return {}
        recent = self.coordinator.data.get("recent", [])
        projects = self.coordinator.data.get("projects", {})
        entries = []
        for i, entry in enumerate(recent):
            project_id = entry.get("projectId")
            project_name = projects.get(project_id, "No project") if project_id else "No project"
            entries.append({
                "index": i + 1,
                "description": entry.get("description") or "No description",
                "project": project_name,
                "duration": self._format_duration(entry),
                "start": entry.get("timeInterval", {}).get("start"),
                "end": entry.get("timeInterval", {}).get("end"),
                "billable": entry.get("billable", False),
            })
        return {"entries": entries}


class _ClockifyDayEntriesSensor(ClockifyBaseSensor):
    """Base for sensors that list a day's entries in attributes."""

    _day_key: str = "today"

    def _format_duration(self, entry: dict) -> str:
        interval = entry.get("timeInterval", {})
        start_str = interval.get("start")
        end_str = interval.get("end")
        if not start_str or not end_str:
            return "in progress"
        start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        total_seconds = int((end - start).total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    @property
    def native_value(self) -> int | None:
        if not self.coordinator.data:
            return None
        return len(self.coordinator.data.get(self._day_key, []))

    @property
    def extra_state_attributes(self) -> dict:
        if not self.coordinator.data:
            return {}
        day_entries = self.coordinator.data.get(self._day_key, [])
        projects = self.coordinator.data.get("projects", {})
        entries = []
        for i, entry in enumerate(day_entries):
            project_id = entry.get("projectId")
            project_name = projects.get(project_id, "No project") if project_id else "No project"
            entries.append({
                "index": i + 1,
                "description": entry.get("description") or "No description",
                "project": project_name,
                "duration": self._format_duration(entry),
                "start": entry.get("timeInterval", {}).get("start"),
                "end": entry.get("timeInterval", {}).get("end"),
            })
        return {"entries": entries}


class ClockifyTodayEntriesSensor(_ClockifyDayEntriesSensor):
    _day_key = "today"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "today_entries", "Today's Entries")
        self._attr_icon = "mdi:calendar-today"


class ClockifyYesterdayEntriesSensor(_ClockifyDayEntriesSensor):
    _day_key = "yesterday"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "yesterday_entries", "Yesterday's Entries")
        self._attr_icon = "mdi:calendar-minus"


class ClockifyYesterdayDurationSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "yesterday_duration", "Yesterday's Duration")
        self._attr_icon = "mdi:calendar-clock"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"

    @property
    def native_value(self) -> int:
        if not self.coordinator.data:
            return 0
        yesterday_entries = self.coordinator.data.get("yesterday", [])
        total = 0
        for entry in yesterday_entries:
            interval = entry.get("timeInterval", {})
            start_str = interval.get("start")
            end_str = interval.get("end")
            if not start_str or not end_str:
                continue
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            total += int((end - start).total_seconds())
        return total


class ClockifyTodayDurationSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "today_duration", "Today's Duration")
        self._attr_icon = "mdi:calendar-clock"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"

    def _total_seconds_today(self) -> int:
        if not self.coordinator.data:
            return 0
        today_entries = self.coordinator.data.get("today", [])
        now = datetime.now(timezone.utc)
        total = 0
        for entry in today_entries:
            interval = entry.get("timeInterval", {})
            start_str = interval.get("start")
            if not start_str:
                continue
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_str = interval.get("end")
            if end_str:
                end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            else:
                end = now
            total += int((end - start).total_seconds())
        return total

    @property
    def native_value(self) -> int:
        return self._total_seconds_today()


class _ClockifyFilteredDurationSensor(ClockifyBaseSensor):
    def _get_project_id(self) -> str | None:
        raise NotImplementedError

    def _total_seconds_for_project(self) -> int:
        if not self.coordinator.data:
            return 0
        project_id = self._get_project_id()
        if not project_id:
            return 0
        today_entries = self.coordinator.data.get("today", [])
        now = datetime.now(timezone.utc)
        total = 0
        for entry in today_entries:
            if entry.get("projectId") != project_id:
                continue
            interval = entry.get("timeInterval", {})
            start_str = interval.get("start")
            if not start_str:
                continue
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_str = interval.get("end")
            if end_str:
                end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            else:
                end = now
            total += int((end - start).total_seconds())
        return total

    @property
    def native_value(self) -> int:
        return self._total_seconds_for_project()

    @property
    def extra_state_attributes(self) -> dict:
        projects = self.coordinator.data.get("projects", {}) if self.coordinator.data else {}
        project_id = self._get_project_id()
        return {
            "project": projects.get(project_id, "None") if project_id else "None",
        }


class ClockifyTodayWorkDurationSensor(_ClockifyFilteredDurationSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "today_work_duration", "Today's Work Duration"
        )
        self._attr_icon = "mdi:briefcase-clock-outline"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"

    def _get_project_id(self) -> str | None:
        return self.coordinator.work_project_id


class ClockifyTodayPersonalDurationSensor(_ClockifyFilteredDurationSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "today_personal_duration", "Today's Personal Duration"
        )
        self._attr_icon = "mdi:account-clock-outline"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"

    def _get_project_id(self) -> str | None:
        return self.coordinator.personal_project_id


class ClockifyWeekWorkEntriesSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "week_work_entries", "Week's Work Entries")
        self._attr_icon = "mdi:calendar-week"

    def _filtered_entries(self) -> list[dict]:
        if not self.coordinator.data:
            return []
        project_id = self.coordinator.work_project_id
        if not project_id:
            return []
        return [
            e for e in self.coordinator.data.get("week", [])
            if e.get("projectId") == project_id
        ]

    def _format_duration(self, entry: dict) -> str:
        interval = entry.get("timeInterval", {})
        start_str = interval.get("start")
        end_str = interval.get("end")
        if not start_str or not end_str:
            return "in progress"
        start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        total_seconds = int((end - start).total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    @property
    def native_value(self) -> int:
        return len(self._filtered_entries())

    @property
    def extra_state_attributes(self) -> dict:
        projects = self.coordinator.data.get("projects", {}) if self.coordinator.data else {}
        project_id = self.coordinator.work_project_id
        entries = []
        for i, entry in enumerate(self._filtered_entries()):
            entries.append({
                "index": i + 1,
                "description": entry.get("description") or "No description",
                "duration": self._format_duration(entry),
                "start": entry.get("timeInterval", {}).get("start"),
                "end": entry.get("timeInterval", {}).get("end"),
            })
        return {
            "project": projects.get(project_id, "None") if project_id else "None",
            "entries": entries,
        }


class ClockifyWeekWorkDurationSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "week_work_duration", "Week's Work Duration"
        )
        self._attr_icon = "mdi:calendar-week"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"

    @property
    def native_value(self) -> int:
        if not self.coordinator.data:
            return 0
        project_id = self.coordinator.work_project_id
        if not project_id:
            return 0
        week_entries = self.coordinator.data.get("week", [])
        now = datetime.now(timezone.utc)
        total = 0
        for entry in week_entries:
            if entry.get("projectId") != project_id:
                continue
            interval = entry.get("timeInterval", {})
            start_str = interval.get("start")
            if not start_str:
                continue
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_str = interval.get("end")
            if end_str:
                end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            else:
                end = now
            total += int((end - start).total_seconds())
        return total

    @property
    def extra_state_attributes(self) -> dict:
        projects = self.coordinator.data.get("projects", {}) if self.coordinator.data else {}
        project_id = self.coordinator.work_project_id
        return {
            "project": projects.get(project_id, "None") if project_id else "None",
        }

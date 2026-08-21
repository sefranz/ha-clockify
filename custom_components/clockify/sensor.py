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


def _format_duration(entry: dict) -> str:
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


def _project_name(projects: dict, project_id: str | None) -> str:
    if not project_id:
        return "No project"
    return projects.get(project_id, "Unknown")


def _project_meta(project_details: dict, project_id: str | None) -> dict:
    if not project_id:
        return {}
    return project_details.get(project_id, {})


def _entry_attributes(
    entry: dict, index: int, projects: dict, project_details: dict
) -> dict:
    project_id = entry.get("projectId")
    attrs = {
        "index": index,
        "id": entry.get("id"),
        "description": entry.get("description") or "No description",
        "project": _project_name(projects, project_id),
        "project_id": project_id,
        "duration": _format_duration(entry),
        "start": entry.get("timeInterval", {}).get("start"),
        "end": entry.get("timeInterval", {}).get("end"),
        "billable": entry.get("billable", False),
        "tag_ids": entry.get("tagIds", []),
    }
    meta = _project_meta(project_details, project_id)
    if meta:
        attrs["project_client_id"] = meta.get("client_id")
        attrs["project_color"] = meta.get("color")
        attrs["project_billable"] = meta.get("billable")
    return attrs


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
        entry = self._running_entry
        if not entry:
            return {}
        projects = self.coordinator.data.get("projects", {})
        project_id = entry.get("projectId")
        return {
            "entry_id": entry.get("id"),
            "description": entry.get("description") or "No description",
            "project": _project_name(projects, project_id),
            "project_id": project_id,
            "billable": entry.get("billable", False),
            "tag_ids": entry.get("tagIds", []),
            "start": entry.get("timeInterval", {}).get("start"),
        }


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
        project_id = entry.get("projectId")
        project_details = self.coordinator.data.get("project_details", {})
        attrs = {"project_id": project_id}
        meta = _project_meta(project_details, project_id)
        if meta:
            attrs["project_client_id"] = meta.get("client_id")
            attrs["project_color"] = meta.get("color")
            attrs["project_billable"] = meta.get("billable")
        return attrs


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

    @property
    def extra_state_attributes(self) -> dict:
        entry = self._running_entry
        if not entry:
            return {}
        projects = self.coordinator.data.get("projects", {})
        project_id = entry.get("projectId")
        start = self.native_value
        elapsed_seconds = (
            int((datetime.now(timezone.utc) - start).total_seconds())
            if start
            else None
        )
        return {
            "entry_id": entry.get("id"),
            "description": entry.get("description") or "No description",
            "project": _project_name(projects, project_id),
            "project_id": project_id,
            "billable": entry.get("billable", False),
            "tag_ids": entry.get("tagIds", []),
            "elapsed_seconds": elapsed_seconds,
        }


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

    @property
    def extra_state_attributes(self) -> dict:
        entry = self._running_entry
        if not entry:
            return {}
        projects = self.coordinator.data.get("projects", {})
        project_id = entry.get("projectId")
        return {
            "entry_id": entry.get("id"),
            "project": _project_name(projects, project_id),
            "project_id": project_id,
            "billable": entry.get("billable", False),
            "tag_ids": entry.get("tagIds", []),
            "start": entry.get("timeInterval", {}).get("start"),
        }


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
        projects = self.coordinator.data.get("projects", {})
        project_id = entry.get("projectId")
        return {
            "task_id": entry.get("taskId"),
            "project": _project_name(projects, project_id),
            "project_id": project_id,
        }


class ClockifyRecentEntriesSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "recent_entries", "Recent Entries")
        self._attr_icon = "mdi:history"

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
        project_details = self.coordinator.data.get("project_details", {})
        entries = [
            _entry_attributes(entry, i + 1, projects, project_details)
            for i, entry in enumerate(recent)
        ]
        return {"entries": entries}


class _ClockifyDayEntriesSensor(ClockifyBaseSensor):
    """Base for sensors that list a day's entries in attributes."""

    _day_key: str = "today"

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
        project_details = self.coordinator.data.get("project_details", {})
        entries = [
            _entry_attributes(entry, i + 1, projects, project_details)
            for i, entry in enumerate(day_entries)
        ]
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

    def _entries(self) -> list[dict]:
        if not self.coordinator.data:
            return []
        return self.coordinator.data.get("yesterday", [])

    def _breakdown(self) -> tuple[int, int, int, int]:
        entries = self._entries()
        total = billable = non_billable = 0
        for entry in entries:
            interval = entry.get("timeInterval", {})
            start_str = interval.get("start")
            end_str = interval.get("end")
            if not start_str or not end_str:
                continue
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            seconds = int((end - start).total_seconds())
            total += seconds
            if entry.get("billable", False):
                billable += seconds
            else:
                non_billable += seconds
        return total, billable, non_billable, len(entries)

    @property
    def native_value(self) -> int:
        return self._breakdown()[0]

    @property
    def extra_state_attributes(self) -> dict:
        _total, billable, non_billable, count = self._breakdown()
        return {
            "entry_count": count,
            "billable_seconds": billable,
            "non_billable_seconds": non_billable,
        }


class ClockifyTodayDurationSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "today_duration", "Today's Duration")
        self._attr_icon = "mdi:calendar-clock"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"

    def _breakdown(self) -> tuple[int, int, int, int]:
        if not self.coordinator.data:
            return 0, 0, 0, 0
        today_entries = self.coordinator.data.get("today", [])
        now = datetime.now(timezone.utc)
        total = billable = non_billable = 0
        for entry in today_entries:
            interval = entry.get("timeInterval", {})
            start_str = interval.get("start")
            if not start_str:
                continue
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_str = interval.get("end")
            end = (
                datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                if end_str
                else now
            )
            seconds = int((end - start).total_seconds())
            total += seconds
            if entry.get("billable", False):
                billable += seconds
            else:
                non_billable += seconds
        return total, billable, non_billable, len(today_entries)

    @property
    def native_value(self) -> int:
        return self._breakdown()[0]

    @property
    def extra_state_attributes(self) -> dict:
        _total, billable, non_billable, count = self._breakdown()
        return {
            "entry_count": count,
            "billable_seconds": billable,
            "non_billable_seconds": non_billable,
        }


class _ClockifyFilteredDurationSensor(ClockifyBaseSensor):
    def _get_project_id(self) -> str | None:
        raise NotImplementedError

    def _filtered_entries(self) -> list[dict]:
        if not self.coordinator.data:
            return []
        project_id = self._get_project_id()
        if not project_id:
            return []
        return [
            e for e in self.coordinator.data.get("today", [])
            if e.get("projectId") == project_id
        ]

    @property
    def native_value(self) -> int:
        now = datetime.now(timezone.utc)
        total = 0
        for entry in self._filtered_entries():
            interval = entry.get("timeInterval", {})
            start_str = interval.get("start")
            if not start_str:
                continue
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_str = interval.get("end")
            end = (
                datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                if end_str
                else now
            )
            total += int((end - start).total_seconds())
        return total

    @property
    def extra_state_attributes(self) -> dict:
        projects = self.coordinator.data.get("projects", {}) if self.coordinator.data else {}
        project_details = (
            self.coordinator.data.get("project_details", {})
            if self.coordinator.data
            else {}
        )
        project_id = self._get_project_id()
        attrs = {
            "project": projects.get(project_id, "None") if project_id else "None",
            "project_id": project_id,
            "entry_count": len(self._filtered_entries()),
        }
        meta = _project_meta(project_details, project_id)
        if meta:
            attrs["project_client_id"] = meta.get("client_id")
            attrs["project_color"] = meta.get("color")
            attrs["project_billable"] = meta.get("billable")
        return attrs


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

    @property
    def native_value(self) -> int:
        return len(self._filtered_entries())

    @property
    def extra_state_attributes(self) -> dict:
        projects = self.coordinator.data.get("projects", {}) if self.coordinator.data else {}
        project_details = (
            self.coordinator.data.get("project_details", {})
            if self.coordinator.data
            else {}
        )
        project_id = self.coordinator.work_project_id
        entries = [
            _entry_attributes(entry, i + 1, projects, project_details)
            for i, entry in enumerate(self._filtered_entries())
        ]
        return {
            "project": projects.get(project_id, "None") if project_id else "None",
            "project_id": project_id,
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

    @property
    def native_value(self) -> int:
        now = datetime.now(timezone.utc)
        total = 0
        for entry in self._filtered_entries():
            interval = entry.get("timeInterval", {})
            start_str = interval.get("start")
            if not start_str:
                continue
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_str = interval.get("end")
            end = (
                datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                if end_str
                else now
            )
            total += int((end - start).total_seconds())
        return total

    @property
    def extra_state_attributes(self) -> dict:
        projects = self.coordinator.data.get("projects", {}) if self.coordinator.data else {}
        project_details = (
            self.coordinator.data.get("project_details", {})
            if self.coordinator.data
            else {}
        )
        project_id = self.coordinator.work_project_id
        attrs = {
            "project": projects.get(project_id, "None") if project_id else "None",
            "project_id": project_id,
            "entry_count": len(self._filtered_entries()),
        }
        meta = _project_meta(project_details, project_id)
        if meta:
            attrs["project_client_id"] = meta.get("client_id")
            attrs["project_color"] = meta.get("color")
            attrs["project_billable"] = meta.get("billable")
        return attrs

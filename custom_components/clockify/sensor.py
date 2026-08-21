from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
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
            ClockifyClientSensor(coordinator, entry),
            ClockifyStartTimeSensor(coordinator, entry),
            ClockifyDescriptionSensor(coordinator, entry),
            ClockifyTaskSensor(coordinator, entry),
            ClockifyRecentEntriesSensor(coordinator, entry),
            # Today
            ClockifyTodayEntriesSensor(coordinator, entry),
            ClockifyTodayWorkEntriesSensor(coordinator, entry),
            ClockifyTodayPersonalEntriesSensor(coordinator, entry),
            ClockifyTodayProjectEntriesSensor(coordinator, entry),
            ClockifyTodayDurationSensor(coordinator, entry),
            ClockifyTodayWorkDurationSensor(coordinator, entry),
            ClockifyTodayPersonalDurationSensor(coordinator, entry),
            ClockifyTodayProjectDurationSensor(coordinator, entry),
            # Yesterday
            ClockifyYesterdayEntriesSensor(coordinator, entry),
            ClockifyYesterdayWorkEntriesSensor(coordinator, entry),
            ClockifyYesterdayPersonalEntriesSensor(coordinator, entry),
            ClockifyYesterdayProjectEntriesSensor(coordinator, entry),
            ClockifyYesterdayDurationSensor(coordinator, entry),
            ClockifyYesterdayWorkDurationSensor(coordinator, entry),
            ClockifyYesterdayPersonalDurationSensor(coordinator, entry),
            ClockifyYesterdayProjectDurationSensor(coordinator, entry),
            # Week
            ClockifyWeekEntriesSensor(coordinator, entry),
            ClockifyWeekWorkEntriesSensor(coordinator, entry),
            ClockifyWeekPersonalEntriesSensor(coordinator, entry),
            ClockifyWeekProjectEntriesSensor(coordinator, entry),
            ClockifyWeekDurationSensor(coordinator, entry),
            ClockifyWeekWorkDurationSensor(coordinator, entry),
            ClockifyWeekPersonalDurationSensor(coordinator, entry),
            ClockifyWeekProjectDurationSensor(coordinator, entry),
            # Client-level (work/personal only)
            ClockifyTodayWorkClientDurationSensor(coordinator, entry),
            ClockifyTodayPersonalClientDurationSensor(coordinator, entry),
            ClockifyWeekWorkClientEntriesSensor(coordinator, entry),
            ClockifyWeekWorkClientDurationSensor(coordinator, entry),
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


def _project_ids_for_client(project_details: dict, client_id: str | None) -> set[str]:
    if not client_id:
        return set()
    return {
        project_id
        for project_id, meta in project_details.items()
        if meta.get("client_id") == client_id
    }


def _task_name(entry: dict) -> str:
    if not entry.get("taskId"):
        return "No task"
    task = entry.get("task") or {}
    return task.get("name", "Unknown")


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
        "task": _task_name(entry),
        "task_id": entry.get("taskId"),
        "duration": _format_duration(entry),
        "start": entry.get("timeInterval", {}).get("start"),
        "end": entry.get("timeInterval", {}).get("end"),
        "billable": entry.get("billable", False),
        "tag_ids": entry.get("tagIds", []),
    }
    meta = _project_meta(project_details, project_id)
    if meta:
        attrs["project_client_id"] = meta.get("client_id")
        attrs["project_client"] = meta.get("client_name")
        attrs["project_color"] = meta.get("color")
        attrs["project_billable"] = meta.get("billable")
    return attrs


def _layer_project_id(coordinator: ClockifyDataUpdateCoordinator, layer: str) -> str | None:
    if layer == "work":
        return coordinator.work_project_id
    if layer == "personal":
        return coordinator.personal_project_id
    if layer == "project":
        return coordinator.selected_project_id
    return None


def _period_entries(coordinator_data: dict, period_key: str, project_id: str | None) -> list[dict]:
    entries = coordinator_data.get(period_key, [])
    if project_id is None:
        return entries
    return [e for e in entries if e.get("projectId") == project_id]


def _duration_breakdown(
    entries: list[dict], treat_open_as_now: bool
) -> tuple[int, int, int, int]:
    now = datetime.now(timezone.utc)
    total = billable = non_billable = 0
    for entry in entries:
        interval = entry.get("timeInterval", {})
        start_str = interval.get("start")
        if not start_str:
            continue
        end_str = interval.get("end")
        if not end_str:
            if not treat_open_as_now:
                continue
            end = now
        else:
            end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        seconds = int((end - start).total_seconds())
        total += seconds
        if entry.get("billable", False):
            billable += seconds
        else:
            non_billable += seconds
    return total, billable, non_billable, len(entries)


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Clockify",
        manufacturer="Clockify",
        entry_type=DeviceEntryType.SERVICE,
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
        self._attr_device_info = _device_info(entry)

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
            "task": _task_name(entry),
            "task_id": entry.get("taskId"),
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
        attrs = {
            "project_id": project_id,
            "task": _task_name(entry),
            "task_id": entry.get("taskId"),
        }
        meta = _project_meta(project_details, project_id)
        if meta:
            attrs["project_client_id"] = meta.get("client_id")
            attrs["project_client"] = meta.get("client_name")
            attrs["project_color"] = meta.get("color")
            attrs["project_billable"] = meta.get("billable")
        return attrs


class ClockifyClientSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "client", "Tracking: Client")
        self._attr_icon = "mdi:domain"

    @property
    def native_value(self) -> str | None:
        entry = self._running_entry
        if not entry:
            return None
        project_id = entry.get("projectId")
        if not project_id:
            return "No project"
        project_details = self.coordinator.data.get("project_details", {})
        meta = _project_meta(project_details, project_id)
        return meta.get("client_name") or "No client"

    @property
    def extra_state_attributes(self) -> dict:
        entry = self._running_entry
        if not entry:
            return {}
        projects = self.coordinator.data.get("projects", {})
        project_id = entry.get("projectId")
        project_details = self.coordinator.data.get("project_details", {})
        meta = _project_meta(project_details, project_id)
        return {
            "client_id": meta.get("client_id"),
            "project": _project_name(projects, project_id),
            "project_id": project_id,
        }


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
            "task": _task_name(entry),
            "task_id": entry.get("taskId"),
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
            "task": _task_name(entry),
            "task_id": entry.get("taskId"),
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


class _ClockifyLayeredEntriesSensor(ClockifyBaseSensor):
    """Base for entry-count/list sensors filtered by a period + layer.

    Layer is one of "overall", "work", "personal", "project" — resolved to a
    project_id (or None for "overall") via the matching coordinator selection.
    """

    _period_key: str = "today"
    _layer: str = "overall"

    def _get_project_id(self) -> str | None:
        return _layer_project_id(self.coordinator, self._layer)

    def _filtered_entries(self) -> list[dict]:
        if not self.coordinator.data:
            return []
        return _period_entries(self.coordinator.data, self._period_key, self._get_project_id())

    @property
    def native_value(self) -> int | None:
        if not self.coordinator.data:
            return None
        return len(self._filtered_entries())

    @property
    def extra_state_attributes(self) -> dict:
        if not self.coordinator.data:
            return {}
        projects = self.coordinator.data.get("projects", {})
        project_details = self.coordinator.data.get("project_details", {})
        project_id = self._get_project_id()
        entries = [
            _entry_attributes(entry, i + 1, projects, project_details)
            for i, entry in enumerate(self._filtered_entries())
        ]
        if self._layer == "overall":
            attrs = {"project": "All projects", "project_id": None}
        else:
            attrs = {
                "project": projects.get(project_id, "None") if project_id else "None",
                "project_id": project_id,
            }
        attrs["entries"] = entries
        return attrs


class _ClockifyLayeredDurationSensor(ClockifyBaseSensor):
    """Base for duration sensors filtered by a period + layer.

    See _ClockifyLayeredEntriesSensor for what "layer" means. treat_open_as_now
    controls whether a still-running entry counts up to "now" (today/week) or
    is excluded (yesterday, since an open entry there is really still ongoing
    today and would otherwise inflate yesterday's total).
    """

    _period_key: str = "today"
    _layer: str = "overall"
    _treat_open_as_now: bool = True

    def _get_project_id(self) -> str | None:
        return _layer_project_id(self.coordinator, self._layer)

    def _filtered_entries(self) -> list[dict]:
        if not self.coordinator.data:
            return []
        return _period_entries(self.coordinator.data, self._period_key, self._get_project_id())

    @property
    def native_value(self) -> int:
        total, _billable, _non_billable, _count = _duration_breakdown(
            self._filtered_entries(), self._treat_open_as_now
        )
        return total

    @property
    def extra_state_attributes(self) -> dict:
        _total, billable, non_billable, count = _duration_breakdown(
            self._filtered_entries(), self._treat_open_as_now
        )
        project_id = self._get_project_id()
        if self._layer == "overall":
            attrs = {"project": "All projects", "project_id": None}
        else:
            projects = self.coordinator.data.get("projects", {}) if self.coordinator.data else {}
            project_details = (
                self.coordinator.data.get("project_details", {})
                if self.coordinator.data
                else {}
            )
            attrs = {
                "project": projects.get(project_id, "None") if project_id else "None",
                "project_id": project_id,
            }
            meta = _project_meta(project_details, project_id)
            if meta:
                attrs["project_client_id"] = meta.get("client_id")
                attrs["project_client"] = meta.get("client_name")
                attrs["project_color"] = meta.get("color")
                attrs["project_billable"] = meta.get("billable")
        attrs["entry_count"] = count
        attrs["billable_seconds"] = billable
        attrs["non_billable_seconds"] = non_billable
        return attrs


# --- Today ---------------------------------------------------------------

class ClockifyTodayEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "today"
    _layer = "overall"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "today_entries", "Today's Entries")
        self._attr_icon = "mdi:calendar-today"


class ClockifyTodayWorkEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "today"
    _layer = "work"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "today_work_entries", "Today's Work Entries")
        self._attr_icon = "mdi:briefcase-outline"


class ClockifyTodayPersonalEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "today"
    _layer = "personal"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "today_personal_entries", "Today's Personal Entries")
        self._attr_icon = "mdi:account-outline"


class ClockifyTodayProjectEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "today"
    _layer = "project"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "today_project_entries", "Today's Project Entries")
        self._attr_icon = "mdi:folder-outline"


class ClockifyTodayDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "today"
    _layer = "overall"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "today_duration", "Today's Duration")
        self._attr_icon = "mdi:calendar-clock"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyTodayWorkDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "today"
    _layer = "work"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "today_work_duration", "Today's Work Duration"
        )
        self._attr_icon = "mdi:briefcase-clock-outline"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyTodayPersonalDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "today"
    _layer = "personal"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "today_personal_duration", "Today's Personal Duration"
        )
        self._attr_icon = "mdi:account-clock-outline"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyTodayProjectDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "today"
    _layer = "project"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "today_project_duration", "Today's Project Duration"
        )
        self._attr_icon = "mdi:folder-clock-outline"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


# --- Yesterday -------------------------------------------------------------

class ClockifyYesterdayEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "yesterday"
    _layer = "overall"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "yesterday_entries", "Yesterday's Entries")
        self._attr_icon = "mdi:calendar-minus"


class ClockifyYesterdayWorkEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "yesterday"
    _layer = "work"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "yesterday_work_entries", "Yesterday's Work Entries")
        self._attr_icon = "mdi:briefcase-outline"


class ClockifyYesterdayPersonalEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "yesterday"
    _layer = "personal"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "yesterday_personal_entries", "Yesterday's Personal Entries"
        )
        self._attr_icon = "mdi:account-outline"


class ClockifyYesterdayProjectEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "yesterday"
    _layer = "project"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "yesterday_project_entries", "Yesterday's Project Entries"
        )
        self._attr_icon = "mdi:folder-outline"


class ClockifyYesterdayDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "yesterday"
    _layer = "overall"
    _treat_open_as_now = False

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "yesterday_duration", "Yesterday's Duration")
        self._attr_icon = "mdi:calendar-clock"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyYesterdayWorkDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "yesterday"
    _layer = "work"
    _treat_open_as_now = False

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "yesterday_work_duration", "Yesterday's Work Duration"
        )
        self._attr_icon = "mdi:briefcase-clock-outline"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyYesterdayPersonalDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "yesterday"
    _layer = "personal"
    _treat_open_as_now = False

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "yesterday_personal_duration", "Yesterday's Personal Duration"
        )
        self._attr_icon = "mdi:account-clock-outline"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyYesterdayProjectDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "yesterday"
    _layer = "project"
    _treat_open_as_now = False

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "yesterday_project_duration", "Yesterday's Project Duration"
        )
        self._attr_icon = "mdi:folder-clock-outline"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


# --- Week --------------------------------------------------------------

class ClockifyWeekEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "week"
    _layer = "overall"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "week_entries", "Week's Entries")
        self._attr_icon = "mdi:calendar-week"


class ClockifyWeekWorkEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "week"
    _layer = "work"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "week_work_entries", "Week's Work Entries")
        self._attr_icon = "mdi:calendar-week"


class ClockifyWeekPersonalEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "week"
    _layer = "personal"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "week_personal_entries", "Week's Personal Entries")
        self._attr_icon = "mdi:calendar-week"


class ClockifyWeekProjectEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "week"
    _layer = "project"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "week_project_entries", "Week's Project Entries")
        self._attr_icon = "mdi:calendar-week"


class ClockifyWeekDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "week"
    _layer = "overall"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "week_duration", "Week's Duration")
        self._attr_icon = "mdi:calendar-week"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyWeekWorkDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "week"
    _layer = "work"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "week_work_duration", "Week's Work Duration"
        )
        self._attr_icon = "mdi:calendar-week"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyWeekPersonalDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "week"
    _layer = "personal"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "week_personal_duration", "Week's Personal Duration"
        )
        self._attr_icon = "mdi:calendar-week"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyWeekProjectDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "week"
    _layer = "project"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "week_project_duration", "Week's Project Duration"
        )
        self._attr_icon = "mdi:calendar-week"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


# --- Client-level (work/personal only, per user's explicit scope choice) ---

class _ClockifyFilteredClientDurationSensor(ClockifyBaseSensor):
    def _get_client_id(self) -> str | None:
        raise NotImplementedError

    def _filtered_entries(self) -> list[dict]:
        if not self.coordinator.data:
            return []
        project_details = self.coordinator.data.get("project_details", {})
        project_ids = _project_ids_for_client(project_details, self._get_client_id())
        if not project_ids:
            return []
        return [
            e for e in self.coordinator.data.get("today", [])
            if e.get("projectId") in project_ids
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
        clients = self.coordinator.data.get("clients", {}) if self.coordinator.data else {}
        client_id = self._get_client_id()
        return {
            "client": clients.get(client_id, "None") if client_id else "None",
            "client_id": client_id,
            "entry_count": len(self._filtered_entries()),
        }


class ClockifyTodayWorkClientDurationSensor(_ClockifyFilteredClientDurationSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "today_work_client_duration",
            "Today's Work Client Duration",
        )
        self._attr_icon = "mdi:domain"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"

    def _get_client_id(self) -> str | None:
        return self.coordinator.work_client_id


class ClockifyTodayPersonalClientDurationSensor(_ClockifyFilteredClientDurationSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "today_personal_client_duration",
            "Today's Personal Client Duration",
        )
        self._attr_icon = "mdi:domain"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"

    def _get_client_id(self) -> str | None:
        return self.coordinator.personal_client_id


class ClockifyWeekWorkClientEntriesSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "week_work_client_entries", "Week's Work Client Entries"
        )
        self._attr_icon = "mdi:domain"

    def _filtered_entries(self) -> list[dict]:
        if not self.coordinator.data:
            return []
        project_details = self.coordinator.data.get("project_details", {})
        project_ids = _project_ids_for_client(
            project_details, self.coordinator.work_client_id
        )
        if not project_ids:
            return []
        return [
            e for e in self.coordinator.data.get("week", [])
            if e.get("projectId") in project_ids
        ]

    @property
    def native_value(self) -> int:
        return len(self._filtered_entries())

    @property
    def extra_state_attributes(self) -> dict:
        clients = self.coordinator.data.get("clients", {}) if self.coordinator.data else {}
        projects = self.coordinator.data.get("projects", {}) if self.coordinator.data else {}
        project_details = (
            self.coordinator.data.get("project_details", {})
            if self.coordinator.data
            else {}
        )
        client_id = self.coordinator.work_client_id
        entries = [
            _entry_attributes(entry, i + 1, projects, project_details)
            for i, entry in enumerate(self._filtered_entries())
        ]
        return {
            "client": clients.get(client_id, "None") if client_id else "None",
            "client_id": client_id,
            "entries": entries,
        }


class ClockifyWeekWorkClientDurationSensor(ClockifyBaseSensor):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "week_work_client_duration",
            "Week's Work Client Duration",
        )
        self._attr_icon = "mdi:domain"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"

    def _filtered_entries(self) -> list[dict]:
        if not self.coordinator.data:
            return []
        project_details = self.coordinator.data.get("project_details", {})
        project_ids = _project_ids_for_client(
            project_details, self.coordinator.work_client_id
        )
        if not project_ids:
            return []
        return [
            e for e in self.coordinator.data.get("week", [])
            if e.get("projectId") in project_ids
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
        clients = self.coordinator.data.get("clients", {}) if self.coordinator.data else {}
        client_id = self.coordinator.work_client_id
        return {
            "client": clients.get(client_id, "None") if client_id else "None",
            "client_id": client_id,
            "entry_count": len(self._filtered_entries()),
        }

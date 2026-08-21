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
            ClockifyTodayWorkProjectEntriesSensor(coordinator, entry),
            ClockifyTodayPersonalProjectEntriesSensor(coordinator, entry),
            ClockifyTodayProjectEntriesSensor(coordinator, entry),
            ClockifyTodayDurationSensor(coordinator, entry),
            ClockifyTodayWorkProjectDurationSensor(coordinator, entry),
            ClockifyTodayPersonalProjectDurationSensor(coordinator, entry),
            ClockifyTodayProjectDurationSensor(coordinator, entry),
            # Yesterday
            ClockifyYesterdayEntriesSensor(coordinator, entry),
            ClockifyYesterdayWorkProjectEntriesSensor(coordinator, entry),
            ClockifyYesterdayPersonalProjectEntriesSensor(coordinator, entry),
            ClockifyYesterdayProjectEntriesSensor(coordinator, entry),
            ClockifyYesterdayDurationSensor(coordinator, entry),
            ClockifyYesterdayWorkProjectDurationSensor(coordinator, entry),
            ClockifyYesterdayPersonalProjectDurationSensor(coordinator, entry),
            ClockifyYesterdayProjectDurationSensor(coordinator, entry),
            # Week
            ClockifyWeekEntriesSensor(coordinator, entry),
            ClockifyWeekWorkProjectEntriesSensor(coordinator, entry),
            ClockifyWeekPersonalProjectEntriesSensor(coordinator, entry),
            ClockifyWeekProjectEntriesSensor(coordinator, entry),
            ClockifyWeekDurationSensor(coordinator, entry),
            ClockifyWeekWorkProjectDurationSensor(coordinator, entry),
            ClockifyWeekPersonalProjectDurationSensor(coordinator, entry),
            ClockifyWeekProjectDurationSensor(coordinator, entry),
            # Client-level (work/personal only)
            ClockifyTodayWorkClientEntriesSensor(coordinator, entry),
            ClockifyTodayPersonalClientEntriesSensor(coordinator, entry),
            ClockifyTodayWorkClientDurationSensor(coordinator, entry),
            ClockifyTodayPersonalClientDurationSensor(coordinator, entry),
            ClockifyYesterdayWorkClientEntriesSensor(coordinator, entry),
            ClockifyYesterdayPersonalClientEntriesSensor(coordinator, entry),
            ClockifyYesterdayWorkClientDurationSensor(coordinator, entry),
            ClockifyYesterdayPersonalClientDurationSensor(coordinator, entry),
            ClockifyWeekWorkClientEntriesSensor(coordinator, entry),
            ClockifyWeekPersonalClientEntriesSensor(coordinator, entry),
            ClockifyWeekWorkClientDurationSensor(coordinator, entry),
            ClockifyWeekPersonalClientDurationSensor(coordinator, entry),
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


def _layer_client_id(coordinator: ClockifyDataUpdateCoordinator, layer: str) -> str | None:
    if layer == "work":
        return coordinator.work_client_id
    if layer == "personal":
        return coordinator.personal_client_id
    return None


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


class _ClockifyScopedEntriesSensor(ClockifyBaseSensor):
    """Base for entry-count/list sensors scoped to a period + some filter.

    A mixin (_ClockifyProjectLayerMixin or _ClockifyClientLayerMixin) supplies
    _filtered_entries() and _scope_attrs() to define what the filter means.
    """

    _period_key: str = "today"

    def _filtered_entries(self) -> list[dict]:
        raise NotImplementedError

    def _scope_attrs(self) -> dict:
        raise NotImplementedError

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
        entries = [
            _entry_attributes(entry, i + 1, projects, project_details)
            for i, entry in enumerate(self._filtered_entries())
        ]
        attrs = self._scope_attrs()
        attrs["entries"] = entries
        return attrs


class _ClockifyScopedDurationSensor(ClockifyBaseSensor):
    """Base for duration sensors scoped to a period + some filter.

    See _ClockifyScopedEntriesSensor for the mixin contract. treat_open_as_now
    controls whether a still-running entry counts up to "now" (today/week) or
    is excluded (yesterday, since an open entry there is really still ongoing
    today and would otherwise inflate yesterday's total).
    """

    _period_key: str = "today"
    _treat_open_as_now: bool = True

    def _filtered_entries(self) -> list[dict]:
        raise NotImplementedError

    def _scope_attrs(self) -> dict:
        raise NotImplementedError

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
        attrs = self._scope_attrs()
        attrs["entry_count"] = count
        attrs["billable_seconds"] = billable
        attrs["non_billable_seconds"] = non_billable
        return attrs


class _ClockifyProjectLayerMixin:
    """Filters entries by the project resolved from _layer.

    _layer is one of "overall" (no filter — all entries in the period),
    "work", "personal", or "project" (coordinator project selections). Unlike
    "overall", the work/personal/project layers return NO entries until their
    corresponding select actually has something picked — they must never
    silently fall back to "all entries".
    """

    _layer: str = "overall"

    def _get_project_id(self) -> str | None:
        return _layer_project_id(self.coordinator, self._layer)

    def _filtered_entries(self) -> list[dict]:
        if not self.coordinator.data:
            return []
        period_entries = self.coordinator.data.get(self._period_key, [])
        if self._layer == "overall":
            return period_entries
        project_id = self._get_project_id()
        if not project_id:
            return []
        return [e for e in period_entries if e.get("projectId") == project_id]

    def _scope_attrs(self) -> dict:
        if self._layer == "overall":
            return {"project": "All projects", "project_id": None}
        projects = self.coordinator.data.get("projects", {}) if self.coordinator.data else {}
        project_details = (
            self.coordinator.data.get("project_details", {}) if self.coordinator.data else {}
        )
        project_id = self._get_project_id()
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
        return attrs


class _ClockifyClientLayerMixin:
    """Filters entries by every project belonging to the client resolved
    from _layer ("work" or "personal" — coordinator client selections),
    aggregating across all of that client's projects, not just one. Same
    "no selection -> no entries" rule as _ClockifyProjectLayerMixin.
    """

    _layer: str = "work"

    def _get_client_id(self) -> str | None:
        return _layer_client_id(self.coordinator, self._layer)

    def _filtered_entries(self) -> list[dict]:
        if not self.coordinator.data:
            return []
        client_id = self._get_client_id()
        if not client_id:
            return []
        project_details = self.coordinator.data.get("project_details", {})
        project_ids = _project_ids_for_client(project_details, client_id)
        if not project_ids:
            return []
        period_entries = self.coordinator.data.get(self._period_key, [])
        return [e for e in period_entries if e.get("projectId") in project_ids]

    def _scope_attrs(self) -> dict:
        clients = self.coordinator.data.get("clients", {}) if self.coordinator.data else {}
        client_id = self._get_client_id()
        return {
            "client": clients.get(client_id, "None") if client_id else "None",
            "client_id": client_id,
        }


class _ClockifyLayeredEntriesSensor(_ClockifyProjectLayerMixin, _ClockifyScopedEntriesSensor):
    """Entry-count/list sensor filtered by a period + project layer."""


class _ClockifyLayeredDurationSensor(_ClockifyProjectLayerMixin, _ClockifyScopedDurationSensor):
    """Duration sensor filtered by a period + project layer."""


class _ClockifyLayeredClientEntriesSensor(_ClockifyClientLayerMixin, _ClockifyScopedEntriesSensor):
    """Entry-count/list sensor filtered by a period + client layer."""


class _ClockifyLayeredClientDurationSensor(_ClockifyClientLayerMixin, _ClockifyScopedDurationSensor):
    """Duration sensor filtered by a period + client layer."""


# --- Today ---------------------------------------------------------------

class ClockifyTodayEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "today"
    _layer = "overall"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "today_entries", "Today Entries")
        self._attr_icon = "mdi:calendar-today"


class ClockifyTodayWorkProjectEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "today"
    _layer = "work"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "today_work_project_entries", "Today Work Project Entries"
        )
        self._attr_icon = "mdi:briefcase-outline"


class ClockifyTodayPersonalProjectEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "today"
    _layer = "personal"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "today_personal_project_entries",
            "Today Personal Project Entries",
        )
        self._attr_icon = "mdi:account-outline"


class ClockifyTodayProjectEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "today"
    _layer = "project"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "today_project_entries", "Today Project Entries")
        self._attr_icon = "mdi:folder-outline"


class ClockifyTodayDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "today"
    _layer = "overall"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "today_duration", "Today Duration")
        self._attr_icon = "mdi:calendar-clock"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyTodayWorkProjectDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "today"
    _layer = "work"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "today_work_project_duration", "Today Work Project Duration"
        )
        self._attr_icon = "mdi:briefcase-clock-outline"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyTodayPersonalProjectDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "today"
    _layer = "personal"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "today_personal_project_duration",
            "Today Personal Project Duration",
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
            coordinator, entry, "today_project_duration", "Today Project Duration"
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
        super().__init__(coordinator, entry, "yesterday_entries", "Yesterday Entries")
        self._attr_icon = "mdi:calendar-minus"


class ClockifyYesterdayWorkProjectEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "yesterday"
    _layer = "work"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "yesterday_work_project_entries",
            "Yesterday Work Project Entries",
        )
        self._attr_icon = "mdi:briefcase-outline"


class ClockifyYesterdayPersonalProjectEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "yesterday"
    _layer = "personal"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "yesterday_personal_project_entries",
            "Yesterday Personal Project Entries",
        )
        self._attr_icon = "mdi:account-outline"


class ClockifyYesterdayProjectEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "yesterday"
    _layer = "project"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "yesterday_project_entries", "Yesterday Project Entries"
        )
        self._attr_icon = "mdi:folder-outline"


class ClockifyYesterdayDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "yesterday"
    _layer = "overall"
    _treat_open_as_now = False

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "yesterday_duration", "Yesterday Duration")
        self._attr_icon = "mdi:calendar-clock"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyYesterdayWorkProjectDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "yesterday"
    _layer = "work"
    _treat_open_as_now = False

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "yesterday_work_project_duration",
            "Yesterday Work Project Duration",
        )
        self._attr_icon = "mdi:briefcase-clock-outline"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyYesterdayPersonalProjectDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "yesterday"
    _layer = "personal"
    _treat_open_as_now = False

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "yesterday_personal_project_duration",
            "Yesterday Personal Project Duration",
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
            coordinator, entry, "yesterday_project_duration", "Yesterday Project Duration"
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
        super().__init__(coordinator, entry, "week_entries", "Week Entries")
        self._attr_icon = "mdi:calendar-week"


class ClockifyWeekWorkProjectEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "week"
    _layer = "work"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "week_work_project_entries", "Week Work Project Entries"
        )
        self._attr_icon = "mdi:calendar-week"


class ClockifyWeekPersonalProjectEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "week"
    _layer = "personal"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "week_personal_project_entries",
            "Week Personal Project Entries",
        )
        self._attr_icon = "mdi:calendar-week"


class ClockifyWeekProjectEntriesSensor(_ClockifyLayeredEntriesSensor):
    _period_key = "week"
    _layer = "project"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "week_project_entries", "Week Project Entries")
        self._attr_icon = "mdi:calendar-week"


class ClockifyWeekDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "week"
    _layer = "overall"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "week_duration", "Week Duration")
        self._attr_icon = "mdi:calendar-week"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyWeekWorkProjectDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "week"
    _layer = "work"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "week_work_project_duration", "Week Work Project Duration"
        )
        self._attr_icon = "mdi:calendar-week"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyWeekPersonalProjectDurationSensor(_ClockifyLayeredDurationSensor):
    _period_key = "week"
    _layer = "personal"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "week_personal_project_duration",
            "Week Personal Project Duration",
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
            coordinator, entry, "week_project_duration", "Week Project Duration"
        )
        self._attr_icon = "mdi:calendar-week"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


# --- Client-level (work/personal only, per user's explicit scope choice) ---
# Same period coverage and architecture as the project grid above, just with
# only 2 layers instead of 4 ("overall"/"project" don't apply to a client
# select the same way).

class ClockifyTodayWorkClientEntriesSensor(_ClockifyLayeredClientEntriesSensor):
    _period_key = "today"
    _layer = "work"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "today_work_client_entries", "Today Work Client Entries"
        )
        self._attr_icon = "mdi:domain"


class ClockifyTodayPersonalClientEntriesSensor(_ClockifyLayeredClientEntriesSensor):
    _period_key = "today"
    _layer = "personal"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "today_personal_client_entries",
            "Today Personal Client Entries",
        )
        self._attr_icon = "mdi:domain"


class ClockifyTodayWorkClientDurationSensor(_ClockifyLayeredClientDurationSensor):
    _period_key = "today"
    _layer = "work"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "today_work_client_duration",
            "Today Work Client Duration",
        )
        self._attr_icon = "mdi:domain"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyTodayPersonalClientDurationSensor(_ClockifyLayeredClientDurationSensor):
    _period_key = "today"
    _layer = "personal"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "today_personal_client_duration",
            "Today Personal Client Duration",
        )
        self._attr_icon = "mdi:domain"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyYesterdayWorkClientEntriesSensor(_ClockifyLayeredClientEntriesSensor):
    _period_key = "yesterday"
    _layer = "work"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "yesterday_work_client_entries",
            "Yesterday Work Client Entries",
        )
        self._attr_icon = "mdi:domain"


class ClockifyYesterdayPersonalClientEntriesSensor(_ClockifyLayeredClientEntriesSensor):
    _period_key = "yesterday"
    _layer = "personal"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "yesterday_personal_client_entries",
            "Yesterday Personal Client Entries",
        )
        self._attr_icon = "mdi:domain"


class ClockifyYesterdayWorkClientDurationSensor(_ClockifyLayeredClientDurationSensor):
    _period_key = "yesterday"
    _layer = "work"
    _treat_open_as_now = False

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "yesterday_work_client_duration",
            "Yesterday Work Client Duration",
        )
        self._attr_icon = "mdi:domain"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyYesterdayPersonalClientDurationSensor(_ClockifyLayeredClientDurationSensor):
    _period_key = "yesterday"
    _layer = "personal"
    _treat_open_as_now = False

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "yesterday_personal_client_duration",
            "Yesterday Personal Client Duration",
        )
        self._attr_icon = "mdi:domain"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyWeekWorkClientEntriesSensor(_ClockifyLayeredClientEntriesSensor):
    _period_key = "week"
    _layer = "work"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator, entry, "week_work_client_entries", "Week Work Client Entries"
        )
        self._attr_icon = "mdi:domain"


class ClockifyWeekPersonalClientEntriesSensor(_ClockifyLayeredClientEntriesSensor):
    _period_key = "week"
    _layer = "personal"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "week_personal_client_entries",
            "Week Personal Client Entries",
        )
        self._attr_icon = "mdi:domain"


class ClockifyWeekWorkClientDurationSensor(_ClockifyLayeredClientDurationSensor):
    _period_key = "week"
    _layer = "work"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "week_work_client_duration",
            "Week Work Client Duration",
        )
        self._attr_icon = "mdi:domain"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"


class ClockifyWeekPersonalClientDurationSensor(_ClockifyLayeredClientDurationSensor):
    _period_key = "week"
    _layer = "personal"
    _treat_open_as_now = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(
            coordinator,
            entry,
            "week_personal_client_duration",
            "Week Personal Client Duration",
        )
        self._attr_icon = "mdi:domain"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "s"
        self._attr_suggested_unit_of_measurement = "h"

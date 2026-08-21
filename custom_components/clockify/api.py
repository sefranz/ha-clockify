from datetime import datetime, timedelta, timezone

import aiohttp

from .const import API_BASE_URL, RECENT_ENTRIES_LIMIT


class ClockifyApiClient:
    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        self._session = session
        self._headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    async def _request(self, method: str, path: str, **kwargs) -> dict | list | None:
        url = f"{API_BASE_URL}{path}"
        async with self._session.request(
            method, url, headers=self._headers, **kwargs
        ) as resp:
            resp.raise_for_status()
            if resp.status == 204:
                return None
            return await resp.json()

    async def get_user(self) -> dict:
        return await self._request("GET", "/user")

    async def get_workspaces(self) -> list[dict]:
        return await self._request("GET", "/workspaces")

    async def get_projects(self, workspace_id: str) -> list[dict]:
        return await self._request("GET", f"/workspaces/{workspace_id}/projects")

    async def get_tasks(self, workspace_id: str, project_id: str) -> list[dict]:
        return await self._request(
            "GET", f"/workspaces/{workspace_id}/projects/{project_id}/tasks"
        )

    async def get_running_entry(self, workspace_id: str, user_id: str) -> dict | None:
        entries = await self._request(
            "GET",
            f"/workspaces/{workspace_id}/user/{user_id}/time-entries",
            params={"in-progress": "true", "hydrated": "true"},
        )
        if entries:
            return entries[0]
        return None

    async def get_recent_entries(
        self, workspace_id: str, user_id: str, limit: int = RECENT_ENTRIES_LIMIT
    ) -> list[dict]:
        return await self._request(
            "GET",
            f"/workspaces/{workspace_id}/user/{user_id}/time-entries",
            params={"page-size": str(limit), "hydrated": "true"},
        )

    async def get_today_entries(
        self, workspace_id: str, user_id: str
    ) -> list[dict]:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return await self._request(
            "GET",
            f"/workspaces/{workspace_id}/user/{user_id}/time-entries",
            params={
                "start": today_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "page-size": "200",
                "hydrated": "true",
            },
        )

    async def get_yesterday_entries(
        self, workspace_id: str, user_id: str
    ) -> list[dict]:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        yesterday_start = today_start - timedelta(days=1)
        return await self._request(
            "GET",
            f"/workspaces/{workspace_id}/user/{user_id}/time-entries",
            params={
                "start": yesterday_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end": today_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "page-size": "200",
                "hydrated": "true",
            },
        )

    async def get_week_entries(
        self, workspace_id: str, user_id: str
    ) -> list[dict]:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        return await self._request(
            "GET",
            f"/workspaces/{workspace_id}/user/{user_id}/time-entries",
            params={
                "start": week_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "page-size": "500",
                "hydrated": "true",
            },
        )

    async def start_entry(
        self,
        workspace_id: str,
        project_id: str | None = None,
        description: str = "",
        billable: bool = False,
        tag_ids: list[str] | None = None,
        task_id: str | None = None,
    ) -> dict:
        payload = {
            "start": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "description": description,
            "billable": billable,
            "projectId": project_id,
            "tagIds": tag_ids or [],
            "taskId": task_id,
        }
        return await self._request(
            "POST", f"/workspaces/{workspace_id}/time-entries", json=payload
        )

    async def stop_entry(self, workspace_id: str, user_id: str) -> dict:
        payload = {"end": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        return await self._request(
            "PATCH",
            f"/workspaces/{workspace_id}/user/{user_id}/time-entries",
            json=payload,
        )

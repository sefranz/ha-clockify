import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ClockifyApiClient
from .const import DOMAIN


class ClockifyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._api_key: str = ""
        self._workspaces: list[dict] = []
        self._user_id: str = ""

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self._api_key = user_input["api_key"]
            session = async_get_clientsession(self.hass)
            client = ClockifyApiClient(session, self._api_key)
            try:
                user = await client.get_user()
                self._user_id = user["id"]
                self._workspaces = await client.get_workspaces()
            except (aiohttp.ClientError, KeyError):
                errors["base"] = "cannot_connect"
            else:
                if len(self._workspaces) == 1:
                    ws = self._workspaces[0]
                    await self.async_set_unique_id(f"{self._user_id}_{ws['id']}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Clockify ({ws['name']})",
                        data={
                            "api_key": self._api_key,
                            "workspace_id": ws["id"],
                            "user_id": self._user_id,
                        },
                    )
                return await self.async_step_workspace()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("api_key"): str}),
            errors=errors,
        )

    async def async_step_workspace(self, user_input=None):
        if user_input is not None:
            ws_id = user_input["workspace_id"]
            ws_name = next(w["name"] for w in self._workspaces if w["id"] == ws_id)
            await self.async_set_unique_id(f"{self._user_id}_{ws_id}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Clockify ({ws_name})",
                data={
                    "api_key": self._api_key,
                    "workspace_id": ws_id,
                    "user_id": self._user_id,
                },
            )

        workspace_options = {ws["id"]: ws["name"] for ws in self._workspaces}
        return self.async_show_form(
            step_id="workspace",
            data_schema=vol.Schema(
                {vol.Required("workspace_id"): vol.In(workspace_options)}
            ),
        )

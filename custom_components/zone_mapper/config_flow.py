"""
Config flow for Zone Mapper.

This integration is UI-configurable and requires no options. The flow simply
creates a single entry so users don't need to add `zone_mapper:` to YAML.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN


class ZoneMapperConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow to create a single Zone Mapper entry."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show a confirmation form and create the entry when submitted."""
        # Prevent multiple entries; this integration is singleton.
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Zone Mapper", data={})

        # Show a confirmation form with no fields
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

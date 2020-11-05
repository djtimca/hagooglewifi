"""Config flow for Google Wifi."""
import logging

import voluptuous as vol
from googlewifi import GoogleWifi
from homeassistant import config_entries
from homeassistant.helpers import aiohttp_client, config_entry_flow

from .const import DOMAIN, REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GoogleWifi."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        config_entry = self.hass.config_entries.async_entries(DOMAIN)
        if config_entry:
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            session = aiohttp_client.async_get_clientsession(self.hass)

            token = user_input[REFRESH_TOKEN]
            api_client = GoogleWifi(token, session)

            try:
                await api_client.connect()
            except ValueError:
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[REFRESH_TOKEN])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Google Wifi", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(REFRESH_TOKEN): str,
                }
            ),
            errors=errors,
        )

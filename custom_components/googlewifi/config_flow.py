"""Config flow for Google Wifi."""
import logging
import secrets

import voluptuous as vol
from googlewifi import GoogleWifi, GoogleWifiAuthError, GoogleWifiException
from homeassistant import config_entries
from homeassistant.const import (
    CONF_SCAN_INTERVAL,
    UnitOfDataRate
)
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client

from .const import (
    ADD_DISABLED,
    CONF_ANDROID_ID,
    CONF_EMAIL,
    CONF_MASTER_TOKEN,
    CONF_OAUTH_TOKEN,
    CONF_SPEED_UNITS,
    CONF_SPEEDTEST,
    CONF_SPEEDTEST_INTERVAL,
    DEFAULT_SPEEDTEST,
    DEFAULT_SPEEDTEST_INTERVAL,
    DOMAIN,
    POLLING_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

MASTER_TOKEN_PREFIXES = ("aas_et/", "oauth2rt_1/")

DESCRIPTION_PLACEHOLDERS = {
    "embedded_setup_url": "https://accounts.google.com/EmbeddedSetup",
    "accounts_url": "https://accounts.google.com",
}


def _credentials_schema(default_email: str = "") -> vol.Schema:
    """Return the credential collection schema."""
    return vol.Schema(
        {
            vol.Required(CONF_EMAIL, default=default_email): str,
            vol.Required(CONF_OAUTH_TOKEN): str,
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GoogleWifi."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def _async_validate_credentials(self, user_input, errors):
        """Exchange the oauth_token if needed and validate the credentials."""
        session = aiohttp_client.async_get_clientsession(self.hass)

        email = user_input[CONF_EMAIL].strip().lower()
        token_input = user_input[CONF_OAUTH_TOKEN].strip()
        android_id = secrets.token_hex(8)

        if token_input.startswith(MASTER_TOKEN_PREFIXES):
            master_token = token_input
        else:
            try:
                master_token = await GoogleWifi.exchange_oauth_token(
                    email=email,
                    oauth_token=token_input,
                    android_id=android_id,
                )
            except GoogleWifiAuthError as err:
                _LOGGER.warning("Google Wifi oauth_token exchange failed: %s", err)
                errors["base"] = "invalid_auth"
                return None
            except ConnectionError as err:
                _LOGGER.warning("Google Wifi token exchange connect error: %s", err)
                errors["base"] = "cannot_connect"
                return None
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
                return None

        api_client = GoogleWifi(
            email=email,
            master_token=master_token,
            android_id=android_id,
            session=session,
        )

        try:
            if not await api_client.connect():
                errors["base"] = "invalid_auth"
                return None
            await api_client.get_systems()
        except (GoogleWifiAuthError, ValueError) as err:
            _LOGGER.warning("Google Wifi authentication failed: %s", err)
            errors["base"] = "invalid_auth"
            return None
        except (ConnectionError, GoogleWifiException) as err:
            _LOGGER.warning("Google Wifi connection failed: %s", err)
            errors["base"] = "cannot_connect"
            return None
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
            return None

        return {
            CONF_EMAIL: email,
            CONF_MASTER_TOKEN: master_token,
            CONF_ANDROID_ID: android_id,
        }

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        config_entry = self.hass.config_entries.async_entries(DOMAIN)
        if config_entry:
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            credentials = await self._async_validate_credentials(user_input, errors)
            if credentials:
                credentials[ADD_DISABLED] = user_input.get(ADD_DISABLED, True)
                await self.async_set_unique_id(credentials[CONF_EMAIL])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Google Wifi", data=credentials)

        return self.async_show_form(
            step_id="user",
            data_schema=_credentials_schema().extend(
                {vol.Required(ADD_DISABLED, default=True): bool}
            ),
            errors=errors,
            description_placeholders=DESCRIPTION_PLACEHOLDERS,
        )

    async def async_step_reauth(self, entry_data):
        """Handle re-authentication when the stored token is rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Collect new credentials for an existing entry."""
        errors = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            credentials = await self._async_validate_credentials(user_input, errors)
            if credentials:
                credentials[ADD_DISABLED] = reauth_entry.data.get(
                    ADD_DISABLED, True
                )
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates=credentials,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_credentials_schema(
                default_email=reauth_entry.data.get(CONF_EMAIL, "")
            ),
            errors=errors,
            description_placeholders=DESCRIPTION_PLACEHOLDERS,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow changes."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, POLLING_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=3),
                    ),
                    vol.Optional(
                        CONF_SPEEDTEST,
                        default=self.config_entry.options.get(
                            CONF_SPEEDTEST, DEFAULT_SPEEDTEST
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_SPEEDTEST_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SPEEDTEST_INTERVAL, DEFAULT_SPEEDTEST_INTERVAL
                        ),
                    ): vol.Coerce(int),
                    vol.Optional(
                        CONF_SPEED_UNITS,
                        default=self.config_entry.options.get(
                            CONF_SPEED_UNITS, UnitOfDataRate.MEGABITS_PER_SECOND
                        ),
                    ): vol.In(
                        {
                            UnitOfDataRate.KILOBITS_PER_SECOND: "kbits/s",
                            UnitOfDataRate.MEGABITS_PER_SECOND: "Mbit/s",
                            UnitOfDataRate.GIGABITS_PER_SECOND: "Gbit/s",
                            UnitOfDataRate.BYTES_PER_SECOND: "B/s",
                            UnitOfDataRate.KILOBYTES_PER_SECOND: "kB/s",
                            UnitOfDataRate.MEGABYTES_PER_SECOND: "MB/s",
                            UnitOfDataRate.GIGABYTES_PER_SECOND: "GB/s",
                        }
                    ),
                }
            ),
        )

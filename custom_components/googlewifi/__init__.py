"""The Google Wifi Integration for Home Assistant."""
import asyncio
import logging
import time
from datetime import timedelta

import voluptuous as vol
from googlewifi import (
    GoogleHomeIgnoreDevice,
    GoogleWifi,
    GoogleWifiAuthError,
    GoogleWifiException,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    ADD_DISABLED,
    CONF_ANDROID_ID,
    CONF_EMAIL,
    CONF_MASTER_TOKEN,
    CONF_SPEEDTEST,
    CONF_SPEEDTEST_INTERVAL,
    COORDINATOR,
    DEFAULT_SPEEDTEST,
    DEFAULT_SPEEDTEST_INTERVAL,
    DOMAIN,
    GOOGLEWIFI_API,
    POLLING_INTERVAL,
    SIGNAL_ADD_DEVICE,
    SIGNAL_DELETE_DEVICE,
)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)
_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "device_tracker", "switch", "light", "sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Google WiFi component."""
    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Google WiFi component from a config entry."""
    polling_interval = entry.options.get(CONF_SCAN_INTERVAL, POLLING_INTERVAL)

    conf = entry.data
    conf_options = entry.options

    if not conf.get(CONF_MASTER_TOKEN):
        # Legacy entries only stored a refresh token which can no longer be
        # exchanged for an API token. Force the user through reauth.
        raise ConfigEntryAuthFailed("Google Wifi requires re-authentication")

    session = aiohttp_client.async_get_clientsession(hass)

    credentials = {
        CONF_EMAIL: conf[CONF_EMAIL],
        CONF_MASTER_TOKEN: conf[CONF_MASTER_TOKEN],
        CONF_ANDROID_ID: conf[CONF_ANDROID_ID],
    }

    api = GoogleWifi(**credentials, session=session)

    try:
        await api.connect()
    except GoogleWifiAuthError as error:
        _LOGGER.debug(f"Google WiFi API: {error}")
        raise ConfigEntryAuthFailed from error
    except (ConnectionError, ValueError) as error:
        _LOGGER.debug(f"Google WiFi API: {error}")
        raise ConfigEntryNotReady from error

    coordinator = GoogleWiFiUpdater(
        hass,
        api=api,
        name="GoogleWifi",
        polling_interval=polling_interval,
        credentials=credentials,
        entry=entry,
        add_disabled=conf.get(ADD_DISABLED, True),
        auto_speedtest=conf_options.get(CONF_SPEEDTEST, DEFAULT_SPEEDTEST),
        speedtest_interval=conf_options.get(
            CONF_SPEEDTEST_INTERVAL, DEFAULT_SPEEDTEST_INTERVAL
        ),
    )

    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
        GOOGLEWIFI_API: api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Migrate legacy config entries to the current version."""
    if entry.version < 2:
        data = dict(entry.data)
        # The legacy refresh token cannot be converted; reauth handles it.
        data.pop("refresh_token", None)
        hass.config_entries.async_update_entry(entry, data=data, version=2)

    return True


async def cleanup_device_registry(hass: HomeAssistant, device_id):
    """Remove device registry entry if there are no remaining entities."""

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    if device_id and not er.async_entries_for_device(
        entity_registry, device_id, include_disabled_entities=True
    ):
        device_registry.async_remove_device(device_id)


class GoogleWiFiUpdater(DataUpdateCoordinator):
    """Class to manage fetching update data from the Google Wifi API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: str,
        name: str,
        polling_interval: int,
        credentials: dict,
        entry: ConfigEntry,
        add_disabled: bool,
        auto_speedtest: str,
        speedtest_interval: str,
    ):
        """Initialize the global Google Wifi data updater."""
        self.api = api
        self.credentials = credentials
        self.entry = entry
        self.add_disabled = add_disabled
        self._last_speedtest = 0
        self.auto_speedtest = auto_speedtest
        self.speedtest_interval = speedtest_interval
        self._force_speed_update = None
        self.devicelist = {}

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=name,
            update_interval=timedelta(seconds=polling_interval),
        )

    async def force_speed_test(self, system_id):
        """Set the flag to force a speed test."""
        self._force_speed_update = system_id
        return True

    async def _async_update_data(self):
        """Fetch data from Google Wifi API."""

        try:
            system_data = await self.api.get_systems()

            for old_system_id in list(self.devicelist):
                if old_system_id not in system_data:
                    for known_device in self.devicelist.pop(old_system_id):
                        async_dispatcher_send(
                            self.hass,
                            SIGNAL_DELETE_DEVICE,
                            {
                                "system_id": old_system_id,
                                "device_id": known_device,
                            },
                        )

            for system_id, system in system_data.items():
                connected_count = 0
                guest_connected_count = 0
                system_devices = self.devicelist.setdefault(system_id, set())
                main_network = system["groupSettings"]["lanSettings"].get(
                    "dhcpPoolBegin", " " * 10
                )
                main_network = ".".join(main_network.split(".", 3)[:3])

                for device_id, device in system["devices"].items():
                    device_network = device.get("ipAddress", " " * 10)
                    device_network = ".".join(device_network.split(".", 3)[:3])

                    if device_id not in system_devices:
                        to_add = {
                            "system_id": system_id,
                            "device_id": device_id,
                            "device": device,
                        }
                        async_dispatcher_send(self.hass, SIGNAL_ADD_DEVICE, to_add)
                        system_devices.add(device_id)

                    if device.get("connected") and main_network == device_network:
                        connected_count += 1
                        device["network"] = "main"
                    elif (
                        device.get("connected")
                        and device.get("unfilteredFriendlyType") != "Nest Wifi point"
                    ):
                        guest_connected_count += 1
                        device["network"] = "guest"
                    elif device.get("unfilteredFriendlyType") == "Nest Wifi point":
                        connected_count += 1
                        device["network"] = "main"

                for known_device in list(system_devices):
                    if known_device not in system["devices"]:
                        async_dispatcher_send(
                            self.hass,
                            SIGNAL_DELETE_DEVICE,
                            {"system_id": system_id, "device_id": known_device},
                        )
                        system_devices.discard(known_device)

                system_data[system_id]["connected_devices"] = connected_count
                system_data[system_id]["guest_devices"] = guest_connected_count
                system_data[system_id]["total_devices"] = (
                    connected_count + guest_connected_count
                )

            if (
                time.time()
                > (self._last_speedtest + (60 * 60 * self.speedtest_interval))
                and self.auto_speedtest == True
                and self.hass.state == CoreState.running
            ):
                for system_id, system in system_data.items():
                    speedtest_result = await self.api.run_speed_test(
                        system_id=system_id
                    )
                    system_data[system_id]["speedtest"] = speedtest_result

                self._last_speedtest = time.time()
            elif self._force_speed_update:
                speedtest_result = await self.api.run_speed_test(
                    system_id=self._force_speed_update
                )
                if self._force_speed_update in system_data:
                    system_data[self._force_speed_update][
                        "speedtest"
                    ] = speedtest_result
                self._force_speed_update = None

            return system_data
        except GoogleWifiAuthError as error:
            self.entry.async_start_reauth(self.hass)
            raise UpdateFailed(
                f"GoogleWifi authentication failed: {error}"
            ) from error
        except GoogleWifiException as error:
            session = aiohttp_client.async_create_clientsession(self.hass)
            self.api = GoogleWifi(**self.credentials, session=session)
            raise UpdateFailed(f"Error connecting to GoogleWifi: {error}") from error
        except GoogleHomeIgnoreDevice as error:
            raise UpdateFailed(f"Error connecting to GoogleWifi: {error}") from error
        except ConnectionError as error:
            raise UpdateFailed(f"Error connecting to GoogleWifi: {error}") from error
        except ValueError as error:
            raise UpdateFailed(f"Invalid data from GoogleWifi: {error}") from error


class GoogleWifiEntity(CoordinatorEntity):
    """Defines the base Google WiFi entity."""

    def __init__(
        self,
        coordinator: GoogleWiFiUpdater,
        name: str,
        icon: str,
        system_id: str,
        item_id: str,
    ):
        """Initialize the Google WiFi Entity."""
        super().__init__(coordinator)

        self._name = name
        self._unique_id = item_id if item_id else system_id
        self._icon = icon
        self._system_id = system_id
        self._item_id = item_id
        self._attrs = {}

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def icon(self):
        """Return the icon for the entity."""
        return self._icon

    @property
    def extra_state_attributes(self):
        """Return the attributes."""
        self._attrs["system"] = self._system_id
        return self._attrs

    @property
    def entity_registry_enabled_default(self):
        """Return option setting to enable or disable by default."""
        return self.coordinator.add_disabled

    def _via_device_id(self):
        """Return the device registry id of the parent system device."""
        device_registry = dr.async_get(self.hass)
        parent = device_registry.async_get_device_by_identifier(
            (DOMAIN, self._system_id)
        )
        return parent.id if parent else None

    async def async_added_to_hass(self):
        """When entity is added to HASS."""
        self.async_on_remove(self.coordinator.async_add_listener(self._update_callback))
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_DELETE_DEVICE, self._delete_callback
            )
        )

    @callback
    def _update_callback(self):
        """Handle device update."""
        self.async_write_ha_state()

    async def _delete_callback(self, payload):
        """Remove the device when it disappears."""

        if not isinstance(payload, dict):
            return

        if (
            payload.get("device_id") != self._item_id
            or payload.get("system_id") != self._system_id
        ):
            return

        entity_registry = er.async_get(self.hass)

        if self.entity_id and entity_registry.async_is_registered(self.entity_id):
            entity_entry = entity_registry.async_get(self.entity_id)
            entity_registry.async_remove(self.entity_id)
            await cleanup_device_registry(self.hass, entity_entry.device_id)
        else:
            await self.async_remove()

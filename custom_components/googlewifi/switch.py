"""Support for Google Wifi Connected Devices as Switch Internet on/off."""
import time

import voluptuous as vol
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import ATTR_NAME, DATA_RATE_MEGABITS_PER_SECOND
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util.dt import as_local, as_timestamp, parse_datetime

from . import GoogleWifiEntity, GoogleWiFiUpdater
from .const import (
    ATTR_CONNECTIONS,
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    CONF_SPEED_UNITS,
    COORDINATOR,
    DEFAULT_ICON,
    DEV_CLIENT_MODEL,
    DOMAIN,
    PAUSE_UPDATE,
    SIGNAL_ADD_DEVICE,
    SIGNAL_DELETE_DEVICE,
    unit_convert,
)

SERVICE_PRIORITIZE = "prioritize"
SERVICE_CLEAR_PRIORITIZATION = "prioritize_reset"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    device = hass.data[DOMAIN][entry.entry_id]

    entities = []

    data_unit = entry.options.get(CONF_SPEED_UNITS, DATA_RATE_MEGABITS_PER_SECOND)

    for system_id, system in coordinator.data.items():
        for dev_id, device in system["devices"].items():
            device_name = f"{device['friendlyName']}"

            if device.get("friendlyType"):
                device_name = device_name + f" ({device['friendlyType']})"

            entity = GoogleWifiSwitch(
                coordinator=coordinator,
                name=device_name,
                icon=DEFAULT_ICON,
                system_id=system_id,
                item_id=dev_id,
                data_unit=data_unit,
            )
            entities.append(entity)

    async_add_entities(entities)

    async def async_new_entities(device_info):
        """Add new entities when they connect to Google Wifi."""
        system_id = device_info["system_id"]
        device_id = device_info["device_id"]
        device = device_info["device"]

        device_name = f"{device['friendlyName']}"

        if device.get("friendlyType"):
            device_name = device_name + f" ({device['friendlyType']})"

        entity = GoogleWifiSwitch(
            coordinator=coordinator,
            name=device_name,
            icon=DEFAULT_ICON,
            system_id=system_id,
            item_id=device_id,
            data_unit=data_unit,
        )
        entities = [entity]
        async_add_entities(entities)

    async_dispatcher_connect(hass, SIGNAL_ADD_DEVICE, async_new_entities)

    # register service for reset
    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SERVICE_PRIORITIZE,
        {vol.Required("duration"): cv.positive_int},
        "async_prioritize_device",
    )

    platform.async_register_entity_service(
        SERVICE_CLEAR_PRIORITIZATION,
        {},
        "async_clear_prioritization",
    )

    return True


class GoogleWifiSwitch(GoogleWifiEntity, SwitchEntity):
    """Defines a Google WiFi switch."""

    def __init__(self, coordinator, name, icon, system_id, item_id, data_unit):
        """Initialize the switch."""
        super().__init__(
            coordinator=coordinator,
            name=name,
            icon=icon,
            system_id=system_id,
            item_id=item_id,
        )

        self._state = None
        self._available = None
        self._last_change = 0
        self._mac = None
        self._unit_of_measurement = data_unit

    @property
    def is_on(self):
        """Return the status of the internet for this device."""
        since_last = int(time.time()) - self._last_change

        if since_last > PAUSE_UPDATE:
            try:
                is_prioritized = False
                is_prioritized_end = "NA"

                if (
                    self.coordinator.data[self._system_id]["groupSettings"][
                        "lanSettings"
                    ]
                    .get("prioritizedStation")
                    .get("stationId")
                ):
                    if (
                        self.coordinator.data[self._system_id]["groupSettings"][
                            "lanSettings"
                        ]["prioritizedStation"]["stationId"]
                        == self._item_id
                    ):
                        end_time = self.coordinator.data[self._system_id][
                            "groupSettings"
                        ]["lanSettings"]["prioritizedStation"]["prioritizationEndTime"]
                        is_prioritized_end = as_local(
                            parse_datetime(end_time)
                        ).strftime("%d-%b-%y %I:%M %p")

                        if as_timestamp(parse_datetime(end_time)) > time.time():
                            is_prioritized = True

                self._attrs["prioritized"] = is_prioritized
                self._attrs["prioritized_end"] = is_prioritized_end

                if self.coordinator.data[self._system_id]["devices"][self._item_id][
                    "paused"
                ]:
                    self._state = False
                else:
                    self._state = True
            except TypeError:
                pass
            except KeyError:
                pass

        if self.coordinator.data:
            self._mac = self.coordinator.data[self._system_id]["devices"][
                self._item_id
            ].get("macAddress", None)

            self._attrs["mac"] = self._mac if self._mac else "NA"
            self._attrs["ip"] = self.coordinator.data[self._system_id]["devices"][
                self._item_id
            ].get("ipAddress", "NA")

            transmit_speed = float(
                self.coordinator.data[self._system_id]["devices"][self._item_id]
                .get("traffic", {})
                .get("transmitSpeedBps", 0)
            )

            receive_speed = float(
                self.coordinator.data[self._system_id]["devices"][self._item_id]
                .get("traffic", {})
                .get("receiveSpeedBps", 0)
            )

            self._attrs[
                f"transmit_speed_{self._unit_of_measurement.replace('/', 'p').replace(' ', '_').lower()}"
            ] = unit_convert(transmit_speed, self._unit_of_measurement)
            self._attrs[
                f"receive_speed_{self._unit_of_measurement.replace('/', 'p').replace(' ', '_').lower()}"
            ] = unit_convert(receive_speed, self._unit_of_measurement)

            self._attrs["network"] = self.coordinator.data[self._system_id]["devices"][
                self._item_id
            ]["network"]

        return self._state

    @property
    def available(self):
        """Switch is not available if it is not connected."""
        try:
            if (
                self.coordinator.data[self._system_id]["devices"][self._item_id].get(
                    "connected"
                )
                == True
            ):
                self._available = True
            else:
                self._available = False
        except TypeError:
            pass
        except KeyError:
            pass

        return self._available

    @property
    def device_info(self):
        """Define the device as a device tracker system."""
        if self._mac:
            mac = {(CONNECTION_NETWORK_MAC, self._mac)}
        else:
            mac = {}

        device_info = {
            ATTR_IDENTIFIERS: {(DOMAIN, self._item_id)},
            ATTR_CONNECTIONS: mac,
            ATTR_NAME: self._name,
            ATTR_MANUFACTURER: "Google",
            ATTR_MODEL: DEV_CLIENT_MODEL,
            "via_device": (DOMAIN, self._system_id),
        }

        return device_info

    async def async_turn_on(self, **kwargs):
        """Turn on (unpause) internet to the client."""
        self._state = True
        self._last_change = time.time()
        self.async_schedule_update_ha_state()
        await self.coordinator.api.pause_device(self._system_id, self._item_id, False)

    async def async_turn_off(self, **kwargs):
        """Turn on (pause) internet to the client."""
        self._state = False
        self._last_change = time.time()
        self.async_schedule_update_ha_state()
        await self.coordinator.api.pause_device(self._system_id, self._item_id, True)

    async def async_prioritize_device(self, duration):
        """Prioritize a device for (optional) x hours."""

        await self.coordinator.api.clear_prioritization(self._system_id)

        await self.coordinator.api.prioritize_device(
            self._system_id,
            self._item_id,
            duration,
        )

    async def async_clear_prioritization(self):
        """Clear previous prioritization."""

        await self.coordinator.api.clear_prioritization(self._system_id)

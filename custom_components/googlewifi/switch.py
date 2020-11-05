"""Support for Google Wifi Connected Devices as Switch Internet on/off."""
<<<<<<< HEAD
import voluptuous as vol
=======
>>>>>>> d8e701979668c4981ea06352d7bce9f3712efee5
import time

import voluptuous as vol
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import ATTR_NAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.util.dt import as_local, parse_datetime

from . import GoogleWifiEntity, GoogleWiFiUpdater
from .const import (
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    COORDINATOR,
    DEFAULT_ICON,
    DEV_CLIENT_MODEL,
<<<<<<< HEAD
=======
    DEV_MANUFACTURER,
    DOMAIN,
>>>>>>> d8e701979668c4981ea06352d7bce9f3712efee5
    PAUSE_UPDATE,
)

SERVICE_PRIORITIZE = "prioritize"
SERVICE_CLEAR_PRIORITIZATION = "prioritize_reset"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities = []

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
            )
            entities.append(entity)

    async_add_entities(entities)

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


class GoogleWifiSwitch(GoogleWifiEntity, SwitchEntity):
    """Defines a Google WiFi switch."""

    def __init__(self, coordinator, name, icon, system_id, item_id):
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

    @property
    def is_on(self):
        """Return the status of the internet for this device."""
        since_last = int(time.time()) - self._last_change

        if since_last > PAUSE_UPDATE:
            try:
                is_prioritized = False
                is_prioritized_end = "NA"

<<<<<<< HEAD
                if self.coordinator.data[self._system_id]["groupSettings"]["lanSettings"].get("prioritizedStation").get("stationId"):
                    if self.coordinator.data[self._system_id]["groupSettings"]["lanSettings"]["prioritizedStation"]["stationId"] == self._item_id:
                        is_prioritized = True
                        end_time = self.coordinator.data[self._system_id]["groupSettings"]["lanSettings"]["prioritizedStation"]["prioritizationEndTime"]
                        is_prioritized_end = as_local(parse_datetime(end_time)).strftime("%d-%b-%y %I:%M %p")

                self._attrs["prioritized"] = is_prioritized
                self._attrs["prioritized_end"] = is_prioritized_end
        
                if self.coordinator.data[self._system_id]["devices"][self._item_id]["paused"]:
=======
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
                        is_prioritized = True
                        end_time = self.coordinator.data[self._system_id][
                            "groupSettings"
                        ]["lanSettings"]["prioritizedStation"]["prioritizationEndTime"]
                        is_prioritized_end = as_local(
                            parse_datetime(end_time)
                        ).strftime("%d-%b-%y %I:%M %p")

                self._attrs["prioritized"] = is_prioritized
                self._attrs["prioritized_end"] = is_prioritized_end

                if self.coordinator.data[self._system_id]["devices"][self._item_id][
                    "paused"
                ]:
>>>>>>> d8e701979668c4981ea06352d7bce9f3712efee5
                    self._state = False
                else:
                    self._state = True
            except TypeError:
                pass

        return self._state

    @property
    def available(self):
        """Switch is not available if it is not connected."""
        try:
<<<<<<< HEAD
            if self.coordinator.data[self._system_id]["devices"][self._item_id].get("connected") == True:
=======
            if (
                self.coordinator.data[self._system_id]["devices"][self._item_id].get(
                    "connected"
                )
                == True
            ):
>>>>>>> d8e701979668c4981ea06352d7bce9f3712efee5
                self._available = True
            else:
                self._available = False
        except TypeError:
            pass

        return self._available

    @property
    def device_info(self):
        """Define the device as a device tracker system."""
        device_info = {
            ATTR_IDENTIFIERS: {(DOMAIN, self._item_id)},
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
        await self.coordinator.api.pause_device(self._system_id, self._item_id, False)

    async def async_turn_off(self, **kwargs):
        """Turn on (pause) internet to the client."""
        self._state = False
        self._last_change = time.time()
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

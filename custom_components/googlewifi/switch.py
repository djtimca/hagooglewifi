"""Support for Google Wifi Connected Devices as Switch Internet on/off."""
import logging

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
    DEV_MANUFACTURER,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

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

    @property
    def is_on(self):
        """Return the status of the internet for this device."""

        is_prioritized = False
        is_prioritized_end = "NA"

        if (
            self.coordinator.data[self._system_id]["groupSettings"]["lanSettings"]
            .get("prioritizedStation")
            .get("stationId")
        ):
            if (
                self.coordinator.data[self._system_id]["groupSettings"]["lanSettings"][
                    "prioritizedStation"
                ]["stationId"]
                == self._item_id
            ):
                is_prioritized = True
                end_time = self.coordinator.data[self._system_id]["groupSettings"][
                    "lanSettings"
                ]["prioritizedStation"]["prioritizationEndTime"]
                is_prioritized_end = as_local(parse_datetime(end_time)).strftime(
                    "%d-%b-%y %I:%M %p"
                )

        self._attrs["prioritized"] = is_prioritized
        self._attrs["prioritized_end"] = is_prioritized_end

        if self.coordinator.data[self._system_id]["devices"][self._item_id]["paused"]:
            return False
        else:
            return True

    @property
    def available(self):
        """Switch is not available if it is not connected."""
        if (
            self.coordinator.data[self._system_id]["devices"][self._item_id].get(
                "connected"
            )
            == True
        ):
            return True
        else:
            return False

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
        await self.coordinator.api.pause_device(self._system_id, self._item_id, False)

    async def async_turn_off(self, **kwargs):
        """Turn on (pause) internet to the client."""
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

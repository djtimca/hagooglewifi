"""Definition and setup of the Google Wifi Sensors for Home Assistant."""

import logging
import voluptuous as vol

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.helpers import config_validation as cv, entity_platform

from . import GoogleWiFiUpdater, GoogleWifiEntity

from .const import DOMAIN, COORDINATOR

_LOGGER = logging.getLogger(__name__)

SERVICE_RESET = "reset"

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the binary sensor platforms."""

    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities = []

    for system_id, system in coordinator.data.items():
        entity = GoogleWifiBinarySensor(
            coordinator=coordinator,
            name=f"Google Wifi System {system_id}",
            icon="mdi:wifi",
            system_id=system_id,
            item_id=None,
        )
        entities.append(entity)

        for ap_id, access_point in system["access_points"].items():
            entity = GoogleWifiBinarySensor(
                coordinator=coordinator,
                name=f"{access_point['accessPointSettings']['accessPointOtherSettings']['roomData']['name']} Access Point",
                icon="mdi:wifi",
                system_id=system_id,
                item_id=ap_id,
            )
            entities.append(entity)

    async_add_entities(entities)

    #register service for reset
    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SERVICE_RESET,
        {},
        "async_reset_device",
    )

class GoogleWifiBinarySensor(GoogleWifiEntity, BinarySensorEntity):
    """Defines a Google WiFi sensor."""

    @property
    def is_on(self) -> bool:
        """Return the on/off state of the sensor."""

        state = False

        if self._item_id:
            if self.coordinator.data[self._system_id]["access_points"][self._item_id]["status"] == "AP_ONLINE":
                state = True
        else:
            if self.coordinator.data[self._system_id]["status"] == "WAN_ONLINE":
                state = True

        self._icon = "mdi:wifi" if state else "mdi:wifi-alert"
        return state

    async def async_reset_device(self):
        """Reset the network or specific access point."""

        if self._item_id:
            success = await self.coordinator.api.restart_ap(self._item_id)

            if success:
                self.async_schedule_update_ha_state()

            else:
                raise ConnectionError("Failed to reset access point.")

        else:
            success = await self.coordinator.api.restart_system(self._system_id)

            if success:
                self.async_schedule_update_ha_state()

            else:
                raise ConnectionError("Failed to reset the Google Wifi system.")

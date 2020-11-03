"""Support for Google Wifi Routers as device tracker."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import ATTR_NAME

from . import GoogleWiFiUpdater, GoogleWifiEntity

from .const import (
    DOMAIN, 
    COORDINATOR, 
    DEFAULT_ICON,
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    DEV_MANUFACTURER,
    DEV_CLIENT_MODEL,
)

_LOGGER = logging.getLogger(__name__)

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

class GoogleWifiSwitch(GoogleWifiEntity, SwitchEntity):
    """Defines a Google WiFi switch."""

    @property
    def is_on(self):
        """Return the status of the internet for this device."""
        if self.coordinator.data[self._system_id]["devices"][self._item_id]["paused"]:
            return False
        else:
            return True

    @property
    def available(self):
        """Switch is not available if it is not connected."""
        if self.coordinator.data[self._system_id]["devices"][self._item_id].get("connected") == True:
            return True
        else:
            return False

    @property
    def device_info(self):
        """Define the device as a device tracker system."""
        device_info =  {
            ATTR_IDENTIFIERS: {(DOMAIN, self._item_id)},
            ATTR_NAME: self._name,
            ATTR_MANUFACTURER: "Google",
            ATTR_MODEL: DEV_CLIENT_MODEL,
            "via_device": (DOMAIN, self._system_id)
        }    
        
        return device_info

    async def async_turn_on(self, **kwargs):
        """Turn on (unpause) internet to the client."""
        success = await self.coordinator.api.pause_device(self._system_id, self._item_id, False)
        
        #if success:
        #    self.async_schedule_update_ha_state()
    
    async def async_turn_off(self, **kwargs):
        """Turn on (pause) internet to the client."""
        success = await self.coordinator.api.pause_device(self._system_id, self._item_id, True)
        
        #if success:
        #    self.async_schedule_update_ha_state()

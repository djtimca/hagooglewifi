"""Support for Google Wifi Router light control."""
import logging

from homeassistant.components.light import SUPPORT_BRIGHTNESS, ATTR_BRIGHTNESS, LightEntity
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
    """Set up the light platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities = []

    for system_id, system in coordinator.data.items():
        for ap_id, access_point in system["access_points"].items():
            entity = GoogleWifiLight(
                coordinator=coordinator,
                name=f"{access_point['accessPointSettings']['accessPointOtherSettings']['roomData']['name']} Access Point",
                icon="mdi:lightbulb",
                system_id=system_id,
                item_id=ap_id,
            )
            entities.append(entity)

    async_add_entities(entities)

class GoogleWifiLight(GoogleWifiEntity, LightEntity):
    """Defines a Google WiFi light."""
    
    def __init__(self, coordinator, name, icon, system_id, item_id):
        """Initialize the entity."""
        super().__init__(
            coordinator = coordinator,
            name = name,
            icon = icon,
            system_id = system_id,
            item_id = item_id,
        )

        self._last_brightness = 50

    @property
    def is_on(self):
        """Return the on/off state of the light."""
        if self.coordinator.data[self._system_id]["access_points"][self._item_id]["accessPointSettings"]["lightingSettings"].get("intensity"):
            return True
        else:
            return False
    
    @property
    def brightness(self):
        """Return the current brightness of the light."""
        brightness = self.coordinator.data[self._system_id]["access_points"][self._item_id]["accessPointSettings"]["lightingSettings"].get("intensity")

        if brightness:
            if brightness > 0:
                self._last_brightness = brightness

            return brightness * 255 / 100
        else:
            return 0

    @property
    def supported_features(self):
        """Return the supported features - only brightness."""

        return SUPPORT_BRIGHTNESS

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
        """Turn on the light."""
        brightness_pct = 50

        if self._last_brightness:
            brightness_pct = self._last_brightness

        if kwargs.get(ATTR_BRIGHTNESS):
            brightness_pct = kwargs[ATTR_BRIGHTNESS]

        brightness = int(brightness_pct * 100 / 255)

        await self.coordinator.api.set_brightness(self._item_id, brightness)

    async def async_turn_off(self, **kwargs):
        """Turn off the light."""
        await self.coordinator.api.set_brightness(self._item_id, 0)


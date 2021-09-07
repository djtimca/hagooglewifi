"""Support for Google Wifi Router light control."""
import time

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    SUPPORT_BRIGHTNESS,
    LightEntity,
)
from homeassistant.const import ATTR_NAME

from . import GoogleWifiEntity, GoogleWiFiUpdater
from .const import (
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    COORDINATOR,
    DEFAULT_ICON,
    DEV_CLIENT_MODEL,
    DOMAIN,
    PAUSE_UPDATE,
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the light platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities = []

    for system_id, system in coordinator.data.items():
        for ap_id, access_point in system["access_points"].items():
            ap_name = "Google Access Point"

            if access_point["accessPointSettings"].get("accessPointOtherSettings"):
                if access_point["accessPointSettings"]["accessPointOtherSettings"].get(
                    "apName"
                ):
                    ap_name = access_point["accessPointSettings"][
                        "accessPointOtherSettings"
                    ]["apName"]

                if access_point["accessPointSettings"]["accessPointOtherSettings"].get(
                    "roomData"
                ):
                    if access_point["accessPointSettings"]["accessPointOtherSettings"][
                        "roomData"
                    ].get("name"):
                        ap_name = f"{access_point['accessPointSettings']['accessPointOtherSettings']['roomData']['name']} Access Point"

            entity = GoogleWifiLight(
                coordinator=coordinator,
                name=ap_name,
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
            coordinator=coordinator,
            name=name,
            icon=icon,
            system_id=system_id,
            item_id=item_id,
        )

        self._last_brightness = 50
        self._state = None
        self._brightness = None
        self._last_change = 0

    @property
    def is_on(self):
        since_last = int(time.time()) - self._last_change

        if since_last > PAUSE_UPDATE:
            """Return the on/off state of the light."""
            try:
                if self.coordinator.data[self._system_id]["access_points"][
                    self._item_id
                ]["accessPointSettings"]["lightingSettings"].get("intensity"):
                    self._state = True
                else:
                    self._state = False
            except TypeError:
                pass
            except KeyError:
                pass

        return self._state

    @property
    def brightness(self):
        """Return the current brightness of the light."""
        since_last = int(time.time()) - self._last_change

        if since_last > PAUSE_UPDATE:
            try:
                brightness = self.coordinator.data[self._system_id]["access_points"][
                    self._item_id
                ]["accessPointSettings"]["lightingSettings"].get("intensity")

                if brightness:
                    if brightness > 0:
                        self._last_brightness = brightness

                    self._brightness = brightness * 255 / 100
                else:
                    self._brightness = 0
            except TypeError:
                pass
            except KeyError:
                pass

        return self._brightness

    @property
    def supported_features(self):
        """Return the supported features - only brightness."""

        return SUPPORT_BRIGHTNESS

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
        """Turn on the light."""
        brightness_pct = 50

        if self._last_brightness:
            brightness_pct = (
                self._last_brightness if self._last_brightness > 0 else brightness_pct
            )

        if kwargs.get(ATTR_BRIGHTNESS):
            brightness_pct = kwargs[ATTR_BRIGHTNESS]

        brightness = int(brightness_pct * 100 / 255)

        self._brightness = brightness_pct
        self._state = True
        self._last_change = int(time.time())

        await self.coordinator.api.set_brightness(self._item_id, brightness)

    async def async_turn_off(self, **kwargs):
        """Turn off the light."""
        self._state = False
        self._last_change = int(time.time())

        await self.coordinator.api.set_brightness(self._item_id, 0)

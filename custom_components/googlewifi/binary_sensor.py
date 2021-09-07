"""Definition and setup of the Google Wifi Sensors for Home Assistant."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import ATTR_NAME
from homeassistant.helpers import entity_platform
from homeassistant.helpers.update_coordinator import UpdateFailed

from . import GoogleWifiEntity, GoogleWiFiUpdater
from .const import (
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_SW_VERSION,
    COORDINATOR,
    DEFAULT_ICON,
    DEV_MANUFACTURER,
    DOMAIN,
)

SERVICE_RESET = "reset"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the binary sensor platforms."""

    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities = []

    for system_id, system in coordinator.data.items():
        entity = GoogleWifiBinarySensor(
            coordinator=coordinator,
            name=f"Google Wifi System {system_id}",
            icon=DEFAULT_ICON,
            system_id=system_id,
            item_id=None,
        )
        entities.append(entity)

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

            entity = GoogleWifiBinarySensor(
                coordinator=coordinator,
                name=ap_name,
                icon=DEFAULT_ICON,
                system_id=system_id,
                item_id=ap_id,
            )
            entities.append(entity)

    async_add_entities(entities)

    # register service for reset
    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SERVICE_RESET,
        {},
        "async_reset_device",
    )


class GoogleWifiBinarySensor(GoogleWifiEntity, BinarySensorEntity):
    """Defines a Google WiFi sensor."""

    def __init__(self, coordinator, name, icon, system_id, item_id):
        """Initialize the sensor."""
        super().__init__(
            coordinator=coordinator,
            name=name,
            icon=icon,
            system_id=system_id,
            item_id=item_id,
        )

        self._state = None
        self._device_info = None

    @property
    def is_on(self) -> bool:
        """Return the on/off state of the sensor."""

        try:
            state = False

            if self._item_id:
                if (
                    self.coordinator.data[self._system_id]["access_points"][
                        self._item_id
                    ]["status"]
                    == "AP_ONLINE"
                ):
                    state = True
            else:
                if self.coordinator.data[self._system_id]["status"] == "WAN_ONLINE":
                    state = True

            self._state = state
        except TypeError:
            pass
        except KeyError:
            pass

        return self._state

    @property
    def device_info(self):
        """Define the device as an individual Google WiFi system."""

        try:
            device_info = {
                ATTR_MANUFACTURER: DEV_MANUFACTURER,
                ATTR_NAME: self._name,
            }

            if self._item_id:
                device_info[ATTR_IDENTIFIERS] = {(DOMAIN, self._item_id)}
                this_data = self.coordinator.data[self._system_id]["access_points"][
                    self._item_id
                ]
                device_info[ATTR_MANUFACTURER] = this_data["accessPointProperties"][
                    "hardwareType"
                ]
                device_info[ATTR_SW_VERSION] = this_data["accessPointProperties"][
                    "firmwareVersion"
                ]
                device_info["via_device"] = (DOMAIN, self._system_id)
            else:
                device_info[ATTR_IDENTIFIERS] = {(DOMAIN, self._system_id)}
                device_info[ATTR_MODEL] = "Google Wifi"
                device_info[ATTR_SW_VERSION] = self.coordinator.data[self._system_id][
                    "groupProperties"
                ]["otherProperties"]["firmwareVersion"]

            self._device_info = device_info
        except TypeError:
            pass
        except KeyError:
            pass

        return self._device_info

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

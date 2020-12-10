"""Support for Google Wifi Routers as device tracker."""

from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.components.device_tracker.const import DOMAIN as DEVICE_TRACKER
from homeassistant.components.device_tracker.const import SOURCE_TYPE_ROUTER
from homeassistant.const import ATTR_NAME
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import GoogleWifiEntity, GoogleWiFiUpdater
from .const import (
    ATTR_CONNECTIONS,
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    COORDINATOR,
    DEFAULT_ICON,
    DEV_CLIENT_MODEL,
    DEV_MANUFACTURER,
    DOMAIN,
    SIGNAL_ADD_DEVICE,
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the device tracker platforms."""

    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities = []

    for system_id, system in coordinator.data.items():
        for dev_id, device in system["devices"].items():
            device_name = f"{device['friendlyName']}"

            if device.get("friendlyType"):
                device_name = device_name + f" ({device['friendlyType']})"

            entity = GoogleWifiDeviceTracker(
                coordinator=coordinator,
                name=device_name,
                icon=DEFAULT_ICON,
                system_id=system_id,
                item_id=dev_id,
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

        entity = GoogleWifiDeviceTracker(
            coordinator=coordinator,
            name=device_name,
            icon=DEFAULT_ICON,
            system_id=system_id,
            item_id=device_id,
        )
        entities = [entity]
        async_add_entities(entities)

    async_dispatcher_connect(hass, SIGNAL_ADD_DEVICE, async_new_entities)


class GoogleWifiDeviceTracker(GoogleWifiEntity, ScannerEntity):
    """Defines a Google WiFi device tracker."""

    def __init__(self, coordinator, name, icon, system_id, item_id):
        """Initialize the device tracker."""
        super().__init__(
            coordinator=coordinator,
            name=name,
            icon=icon,
            system_id=system_id,
            item_id=item_id,
        )

        self._is_connected = None
        self._mac = None

    @property
    def is_connected(self):
        """Return true if the device is connected."""
        try:
            if self.coordinator.data[self._system_id]["devices"][self._item_id].get(
                "connected"
            ):
                connected_ap = self.coordinator.data[self._system_id]["devices"][
                    self._item_id
                ].get("apId")
                if connected_ap:
                    connected_ap = self.coordinator.data[self._system_id][
                        "access_points"
                    ][connected_ap]["accessPointSettings"]["accessPointOtherSettings"][
                        "roomData"
                    ][
                        "name"
                    ]
                    self._attrs["connected_ap"] = connected_ap
                else:
                    self._attrs["connected_ap"] = "NA"

                self._attrs["ip_address"] = self.coordinator.data[self._system_id][
                    "devices"
                ][self._item_id].get("ipAddress", "NA")

                self._mac = self.coordinator.data[self._system_id]["devices"][
                    self._item_id
                ].get("macAddress")

                self._attrs["mac"] = self._mac if self._mac else "NA"

                self._is_connected = True
            else:
                self._is_connected = False
        except TypeError:
            pass
        except KeyError:
            pass
            # self.hass.async_create_task(
            #    self.hass.config_entries.async_reload(self.coordinator.entry.entry_id)
            # )

        return self._is_connected

    @property
    def source_type(self):
        """Return the source type of the client."""
        return SOURCE_TYPE_ROUTER

    @property
    def device_info(self):
        """Define the device as a device tracker system."""
        if self._mac:
            mac = {(CONNECTION_NETWORK_MAC, self._mac)}
        else:
            mac = {}

        device_info = {
            ATTR_IDENTIFIERS: {(DOMAIN, self._item_id)},
            ATTR_NAME: self._name,
            ATTR_CONNECTIONS: mac,
            ATTR_MANUFACTURER: "Google",
            ATTR_MODEL: DEV_CLIENT_MODEL,
            "via_device": (DOMAIN, self._system_id),
        }

        return device_info

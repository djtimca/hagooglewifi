"""Definition and setup of the Google Wifi Speed Sensor for Home Assistant."""

from homeassistant.const import ATTR_NAME, DATA_RATE_MEGABITS_PER_SECOND
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util.dt import as_local, parse_datetime

from . import GoogleWifiEntity, GoogleWiFiUpdater
from .const import (
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_SW_VERSION,
    CONF_SPEED_UNITS,
    COORDINATOR,
    DEFAULT_ICON,
    DEV_MANUFACTURER,
    DOMAIN,
    unit_convert,
)

SERVICE_SPEED_TEST = "speed_test"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform for a Wifi system."""

    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities = []

    for system_id, system in coordinator.data.items():
        entity = GoogleWifiSpeedSensor(
            coordinator=coordinator,
            name=f"Google Wifi System {system_id} Upload Speed",
            icon=DEFAULT_ICON,
            system_id=system_id,
            speed_key="transmitWanSpeedBps",
            speed_type="speed_test",
            unit_of_measure=entry.options.get(
                CONF_SPEED_UNITS, DATA_RATE_MEGABITS_PER_SECOND
            ),
        )
        entities.append(entity)

        entity = GoogleWifiSpeedSensor(
            coordinator=coordinator,
            name=f"Google Wifi System {system_id} Download Speed",
            icon=DEFAULT_ICON,
            system_id=system_id,
            speed_key="receiveWanSpeedBps",
            speed_type="speed_test",
            unit_of_measure=entry.options.get(
                CONF_SPEED_UNITS, DATA_RATE_MEGABITS_PER_SECOND
            ),
        )
        entities.append(entity)

        entity = GoogleWifiSpeedSensor(
            coordinator=coordinator,
            name=f"Google Wifi System {system_id} Upload Traffic",
            icon=DEFAULT_ICON,
            system_id=system_id,
            speed_key="transmitSpeedBps",
            speed_type="realtime",
            unit_of_measure=entry.options.get(
                CONF_SPEED_UNITS, DATA_RATE_MEGABITS_PER_SECOND
            ),
        )
        entities.append(entity)

        entity = GoogleWifiSpeedSensor(
            coordinator=coordinator,
            name=f"Google Wifi System {system_id} Download Traffic",
            icon=DEFAULT_ICON,
            system_id=system_id,
            speed_key="receiveSpeedBps",
            speed_type="realtime",
            unit_of_measure=entry.options.get(
                CONF_SPEED_UNITS, DATA_RATE_MEGABITS_PER_SECOND
            ),
        )
        entities.append(entity)

        entity = GoogleWifiConnectedDevices(
            coordinator=coordinator,
            name=f"Google Wifi System {system_id} Connected Devices",
            icon="mdi:devices",
            system_id=system_id,
            count_type="main",
        )
        entities.append(entity)

        entity = GoogleWifiConnectedDevices(
            coordinator=coordinator,
            name=f"Google Wifi System {system_id} Guest Devices",
            icon="mdi:devices",
            system_id=system_id,
            count_type="guest",
        )
        entities.append(entity)

        entity = GoogleWifiConnectedDevices(
            coordinator=coordinator,
            name=f"Google Wifi System {system_id} Total Devices",
            icon="mdi:devices",
            system_id=system_id,
            count_type="total",
        )
        entities.append(entity)

    async_add_entities(entities)

    # register service for reset
    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SERVICE_SPEED_TEST,
        {},
        "async_speed_test",
    )


class GoogleWifiSpeedSensor(GoogleWifiEntity):
    """Defines a Google WiFi Speed sensor."""

    def __init__(
        self, coordinator, name, icon, system_id, speed_key, speed_type, unit_of_measure
    ):
        """Initialize the sensor."""
        super().__init__(
            coordinator=coordinator,
            name=name,
            icon=icon,
            system_id=system_id,
            item_id=None,
        )

        self._state = None
        self._device_info = None
        self._speed_key = speed_key
        self._speed_type = speed_type
        self.attrs = {}
        self._unit_of_measurement = unit_of_measure

    @property
    def unique_id(self):
        """Return the unique id for this sensor."""
        return f"{self._system_id}_{self._speed_key}"

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            if self._speed_type == "speed_test":
                if self.coordinator.data[self._system_id].get("speedtest"):
                    self._state = float(
                        self.coordinator.data[self._system_id]["speedtest"][
                            self._speed_key
                        ]
                    )

                    self._state = unit_convert(self._state, self._unit_of_measurement)

            elif self._speed_type == "realtime":
                if self.coordinator.data[self._system_id].get("groupTraffic"):
                    self._state = float(
                        self.coordinator.data[self._system_id]["groupTraffic"].get(
                            self._speed_key, 0
                        )
                    )

                    self._state = unit_convert(self._state, self._unit_of_measurement)

            return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of the sensor."""
        return self._unit_of_measurement

    @property
    def device_info(self):
        """Define the device as an individual Google WiFi system."""

        try:
            device_info = {
                ATTR_MANUFACTURER: DEV_MANUFACTURER,
                ATTR_NAME: self._name,
            }

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

    async def async_speed_test(self, **kwargs):
        """Run a speed test."""
        await self.coordinator.force_speed_test(system_id=self._system_id)


class GoogleWifiConnectedDevices(GoogleWifiEntity):
    """Define a connected devices count sensor for Google Wifi."""

    def __init__(self, coordinator, name, icon, system_id, count_type):
        """Initialize the count sensor."""

        super().__init__(
            coordinator=coordinator,
            name=name,
            icon=icon,
            system_id=system_id,
            item_id=None,
        )

        self._count_type = count_type
        self._state = None

    @property
    def unique_id(self):
        """Return the unique id for this sensor."""
        return f"{self._system_id}_device_count_{self._count_type}"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for this sensor."""
        return "Devices"

    @property
    def device_info(self):
        """Define the device as an individual Google WiFi system."""

        try:
            device_info = {
                ATTR_MANUFACTURER: DEV_MANUFACTURER,
                ATTR_NAME: self._name,
            }

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

    @property
    def state(self):
        """Return the current count of connected devices."""

        if self.coordinator.data:
            if self._count_type == "main":
                self._state = self.coordinator.data[self._system_id][
                    "connected_devices"
                ]
            elif self._count_type == "guest":
                self._state = self.coordinator.data[self._system_id]["guest_devices"]
            elif self._count_type == "total":
                self._state = self.coordinator.data[self._system_id]["total_devices"]

        return self._state

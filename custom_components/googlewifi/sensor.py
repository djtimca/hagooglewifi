"""Definition and setup of the Google Wifi Speed Sensor for Home Assistant."""

from homeassistant.util.dt import as_local, parse_datetime
from homeassistant.const import (
    ATTR_NAME, 
    DATA_RATE_BYTES_PER_SECOND,
    DATA_RATE_KILOBYTES_PER_SECOND,
    DATA_RATE_MEGABYTES_PER_SECOND,
    DATA_RATE_GIGABYTES_PER_SECOND,
)
from homeassistant.helpers import entity_platform
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.exceptions import HomeAssistantError

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
    CONF_SPEED_UNITS,
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
            unit_of_measure=entry.options.get(CONF_SPEED_UNITS,DATA_RATE_MEGABYTES_PER_SECOND),
        )
        entities.append(entity)

        entity = GoogleWifiSpeedSensor(
            coordinator=coordinator,
            name=f"Google Wifi System {system_id} Download Speed",
            icon=DEFAULT_ICON,
            system_id=system_id,
            speed_key="receiveWanSpeedBps",
            unit_of_measure=entry.options.get(CONF_SPEED_UNITS,DATA_RATE_MEGABYTES_PER_SECOND),
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

    def __init__(self, coordinator, name, icon, system_id, speed_key, unit_of_measure):
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
        self.attrs = {}
        self._unit_of_measurement = unit_of_measure

    @property
    def unique_id(self):
        """Return the unique id for this sensor."""
        return f"{self._system_id}_{self._speed_key}"

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.coordinator.data[self._system_id].get("speedtest"):
            self._state = float(self.coordinator.data[self._system_id]["speedtest"][self._speed_key])

            if self._unit_of_measurement == DATA_RATE_KILOBYTES_PER_SECOND:
                self._state *= 1000
            elif self._unit_of_measurement == DATA_RATE_MEGABYTES_PER_SECOND:
                self._state *= 1E-6
            elif self._unit_of_measurement == DATA_RATE_GIGABYTES_PER_SECOND:
                self._state *= 1E-9

            self._state = round(self._state,2)
        
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of the sensor."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """Return the state attributes for this sensor."""
        if self.coordinator.data[self._system_id].get("speedtest"):
            self.attrs["last_updated"] = as_local(parse_datetime(self.coordinator.data[self._system_id]["speedtest"]["timestamp"]))
        else:
            self.attrs["last_updated"] = "Never"

        return self.attrs

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

        return self._device_info

    async def async_speed_test(self):
        """Run a speed test."""

        if self._item_id:
            raise HomeAssistantError("Speed Tests can only be run on the main Google Wifi system.")

        else:
            speed_test = await self.coordinator.api.run_speed_test(self._system_id)

            if speed_test:
                self.coordinator.data[self._system_id]["speedtest"] = speed_test
                self.async_schedule_update_ha_state()

            else:
                raise ConnectionError("Failed to run the speed test.")

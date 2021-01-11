"""Constants for the Google WiFi integration."""

from homeassistant.const import (
    ATTR_NAME,
    DATA_RATE_BITS_PER_SECOND,
    DATA_RATE_BYTES_PER_SECOND,
    DATA_RATE_GIGABITS_PER_SECOND,
    DATA_RATE_GIGABYTES_PER_SECOND,
    DATA_RATE_KILOBITS_PER_SECOND,
    DATA_RATE_KILOBYTES_PER_SECOND,
    DATA_RATE_MEGABITS_PER_SECOND,
    DATA_RATE_MEGABYTES_PER_SECOND,
)

DOMAIN = "googlewifi"
COORDINATOR = "coordinator"
GOOGLEWIFI_API = "googlewifi_api"
ATTR_IDENTIFIERS = "identifiers"
ATTR_MANUFACTURER = "manufacturer"
ATTR_MODEL = "model"
ATTR_SW_VERSION = "sw_version"
ATTR_CONNECTIONS = "connections"
POLLING_INTERVAL = 30
REFRESH_TOKEN = "refresh_token"
DEV_MANUFACTURER = "Google"
DEV_CLIENT_MODEL = "Connected Client"
DEFAULT_ICON = "mdi:wifi"
PAUSE_UPDATE = 15
ADD_DISABLED = "add_disabled"
CONF_SPEEDTEST = "auto_speedtest"
DEFAULT_SPEEDTEST = True
CONF_SPEEDTEST_INTERVAL = "speedtest_interval"
DEFAULT_SPEEDTEST_INTERVAL = 24
CONF_SPEED_UNITS = "speed_units"
SIGNAL_ADD_DEVICE = "googlewifi_add_device"
SIGNAL_DELETE_DEVICE = "googlewifi_delete_device"


def unit_convert(data_rate: float, unit_of_measurement: str):
    """Convert the speed based on unit of measure."""

    if unit_of_measurement == DATA_RATE_BYTES_PER_SECOND:
        data_rate *= 0.125
    elif unit_of_measurement == DATA_RATE_KILOBYTES_PER_SECOND:
        data_rate *= 0.000125
    elif unit_of_measurement == DATA_RATE_MEGABYTES_PER_SECOND:
        data_rate *= 1.25e-7
    elif unit_of_measurement == DATA_RATE_GIGABYTES_PER_SECOND:
        data_rate *= 1.25e-10
    elif unit_of_measurement == DATA_RATE_KILOBITS_PER_SECOND:
        data_rate *= 0.001
    elif unit_of_measurement == DATA_RATE_MEGABITS_PER_SECOND:
        data_rate *= 1e-6
    elif unit_of_measurement == DATA_RATE_GIGABITS_PER_SECOND:
        data_rate *= 1e-9

    return round(data_rate, 2)

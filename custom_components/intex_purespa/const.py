"""Constants for the Intex PureSpa (Tuya Local) integration."""

from homeassistant.const import Platform

DOMAIN = "intex_purespa"
DEFAULT_NAME = "Intex PureSpa"

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SWITCH,
    Platform.SENSOR,
]

# Config entry keys
CONF_DEVICE_ID = "device_id"
CONF_LOCAL_KEY = "local_key"
CONF_PROTOCOL_VERSION = "protocol_version"

PROTOCOL_VERSION_AUTO = "auto"
PROTOCOL_VERSIONS = ["3.3", "3.4", "3.5", "3.1"]

# Tuya data points of the Intex PureSpa (product id chsaskllmust5d7a)
DP_SANITIZER = "103"
DP_POWER = "104"
DP_JETS = "105"
DP_FILTER = "106"
DP_BUBBLES = "107"
DP_HEATER = "108"
DP_TARGET_TEMP = "109"
DP_CURRENT_TEMP = "110"
DP_REMAINING_TIME = "114"

# Temperature limits per unit
MIN_TEMP_C = 20
MAX_TEMP_C = 40
MIN_TEMP_F = 68
MAX_TEMP_F = 104

# Any target temperature above this value must be Fahrenheit
# (Celsius targets are 20-40, Fahrenheit targets are 68-104)
FAHRENHEIT_DETECTION_THRESHOLD = 45

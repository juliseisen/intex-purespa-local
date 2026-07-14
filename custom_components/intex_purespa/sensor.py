"""Sensor platform for the Intex PureSpa (Tuya Local) integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IntexPureSpaCoordinator
from .const import DOMAIN, DP_CURRENT_TEMP, DP_REMAINING_TIME
from .entity import IntexPureSpaEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the spa sensors."""
    coordinator: IntexPureSpaCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            IntexPureSpaTemperatureSensor(coordinator, entry),
            IntexPureSpaRemainingTimeSensor(coordinator, entry),
            IntexPureSpaRawStatusSensor(coordinator, entry),
        ]
    )


class IntexPureSpaTemperatureSensor(IntexPureSpaEntity, SensorEntity):
    """Current water temperature of the spa."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: IntexPureSpaCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{self._spa_name} Current Temperature"
        self._attr_unique_id = f"{coordinator.device_id}_current_temperature"

    @property
    def native_value(self) -> float | None:
        """Return the current water temperature."""
        return self.coordinator.data.get(DP_CURRENT_TEMP)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit the spa currently reports in."""
        return self.coordinator.temperature_unit


class IntexPureSpaRemainingTimeSensor(IntexPureSpaEntity, SensorEntity):
    """Remaining heating time reported by the spa."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:timer-sand"

    def __init__(
        self,
        coordinator: IntexPureSpaCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{self._spa_name} Remaining Time"
        self._attr_unique_id = f"{coordinator.device_id}_remaining_time"

    @property
    def native_value(self) -> int | None:
        """Return the remaining time in minutes."""
        return self.coordinator.data.get(DP_REMAINING_TIME)


class IntexPureSpaRawStatusSensor(IntexPureSpaEntity, SensorEntity):
    """Diagnostic sensor exposing all raw Tuya data points.

    Useful to identify additional data points (error codes, unit
    setting, ...) of specific spa models.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:code-json"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: IntexPureSpaCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{self._spa_name} Raw Status"
        self._attr_unique_id = f"{coordinator.device_id}_raw_status"

    @property
    def native_value(self) -> int:
        """Return the number of known data points."""
        return len(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose every raw data point as an attribute."""
        return {f"dp_{dp}": value for dp, value in self.coordinator.data.items()}

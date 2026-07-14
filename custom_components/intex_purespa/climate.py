"""Climate platform for the Intex PureSpa (Tuya Local) integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IntexPureSpaCoordinator
from .const import (
    DOMAIN,
    DP_CURRENT_TEMP,
    DP_HEATER,
    DP_POWER,
    DP_TARGET_TEMP,
    MAX_TEMP_C,
    MAX_TEMP_F,
    MIN_TEMP_C,
    MIN_TEMP_F,
)
from .entity import IntexPureSpaEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the spa heater climate entity."""
    coordinator: IntexPureSpaCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([IntexPureSpaClimate(coordinator, entry)])


class IntexPureSpaClimate(IntexPureSpaEntity, ClimateEntity):
    """Heater control of the Intex PureSpa."""

    _attr_icon = "mdi:pool-thermometer"
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 1

    def __init__(
        self,
        coordinator: IntexPureSpaCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator, entry)
        self._attr_name = self._spa_name
        self._attr_unique_id = f"{coordinator.device_id}_heater"

    @property
    def temperature_unit(self) -> str:
        """Return the unit the spa currently reports in."""
        return self.coordinator.temperature_unit

    @property
    def current_temperature(self) -> float | None:
        """Return the current water temperature."""
        return self.coordinator.data.get(DP_CURRENT_TEMP)

    @property
    def target_temperature(self) -> float | None:
        """Return the target water temperature."""
        return self.coordinator.data.get(DP_TARGET_TEMP)

    @property
    def min_temp(self) -> float:
        """Return the minimum settable temperature."""
        if self.temperature_unit == UnitOfTemperature.CELSIUS:
            return MIN_TEMP_C
        return MIN_TEMP_F

    @property
    def max_temp(self) -> float:
        """Return the maximum settable temperature."""
        if self.temperature_unit == UnitOfTemperature.CELSIUS:
            return MAX_TEMP_C
        return MAX_TEMP_F

    @property
    def hvac_mode(self) -> HVACMode:
        """Return HEAT when the heater is enabled, OFF otherwise."""
        if self.coordinator.data.get(DP_HEATER):
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        """Return the current heater activity."""
        data = self.coordinator.data
        if not data.get(DP_POWER) or not data.get(DP_HEATER):
            return HVACAction.OFF

        current = data.get(DP_CURRENT_TEMP)
        target = data.get(DP_TARGET_TEMP)
        if current is not None and target is not None and current >= target:
            return HVACAction.IDLE
        return HVACAction.HEATING

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.coordinator.async_set_dp(
            DP_TARGET_TEMP, int(round(temperature))
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Enable or disable the heater."""
        if hvac_mode == HVACMode.HEAT:
            # The heater only runs while the spa itself is powered on
            if not self.coordinator.data.get(DP_POWER):
                await self.coordinator.async_set_dp(DP_POWER, True)
            await self.coordinator.async_set_dp(DP_HEATER, True)
        else:
            await self.coordinator.async_set_dp(DP_HEATER, False)

    async def async_turn_on(self) -> None:
        """Turn the heater on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        """Turn the heater off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

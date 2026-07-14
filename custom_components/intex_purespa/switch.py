"""Switch platform for the Intex PureSpa (Tuya Local) integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IntexPureSpaCoordinator
from .const import (
    DOMAIN,
    DP_BUBBLES,
    DP_FILTER,
    DP_HEATER,
    DP_JETS,
    DP_POWER,
    DP_SANITIZER,
)
from .entity import IntexPureSpaEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True)
class IntexSpaSwitchDescription:
    """Describes one switchable spa function."""

    dp: str
    name: str
    icon: str
    # Only create the entity if the spa reports this data point
    # (e.g. jets only exist on jet-equipped models)
    optional: bool = False
    # Unique id suffix; defaults to the lowercased name
    key: str | None = None
    # The spa ignores this function unless it is powered on, so turn
    # the power on first when switching the function on
    requires_power: bool = False


SWITCHES: tuple[IntexSpaSwitchDescription, ...] = (
    IntexSpaSwitchDescription(
        dp=DP_POWER, name="Power", icon="mdi:power-plug-outline"
    ),
    IntexSpaSwitchDescription(
        dp=DP_HEATER,
        name="Heater",
        icon="mdi:radiator",
        # "_heater" is already taken by the climate entity
        key="heater_switch",
        requires_power=True,
    ),
    IntexSpaSwitchDescription(
        dp=DP_FILTER, name="Filter", icon="mdi:air-filter"
    ),
    IntexSpaSwitchDescription(
        dp=DP_BUBBLES, name="Bubbles", icon="mdi:chart-bubble"
    ),
    IntexSpaSwitchDescription(
        dp=DP_JETS, name="Jets", icon="mdi:weather-windy", optional=True
    ),
    IntexSpaSwitchDescription(
        dp=DP_SANITIZER,
        name="Sanitizer",
        icon="mdi:recycle-variant",
        optional=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the spa function switches."""
    coordinator: IntexPureSpaCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        IntexPureSpaSwitch(coordinator, entry, description)
        for description in SWITCHES
        if not description.optional or description.dp in coordinator.data
    )


class IntexPureSpaSwitch(IntexPureSpaEntity, SwitchEntity):
    """One switchable function of the Intex PureSpa."""

    def __init__(
        self,
        coordinator: IntexPureSpaCoordinator,
        entry: ConfigEntry,
        description: IntexSpaSwitchDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry)
        self._dp = description.dp
        self._requires_power = description.requires_power

        self._attr_icon = description.icon
        self._attr_name = f"{self._spa_name} {description.name}"
        self._attr_unique_id = (
            f"{coordinator.device_id}_"
            f"{description.key or description.name.lower()}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if the function is currently on."""
        value = self.coordinator.data.get(self._dp)
        if value is None:
            return None
        return bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the function on."""
        if self._requires_power and not self.coordinator.data.get(DP_POWER):
            await self.coordinator.async_set_dp(DP_POWER, True)
        await self.coordinator.async_set_dp(self._dp, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the function off."""
        await self.coordinator.async_set_dp(self._dp, False)

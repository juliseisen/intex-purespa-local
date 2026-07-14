"""Base entity for the Intex PureSpa (Tuya Local) integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import IntexPureSpaCoordinator
from .const import DEFAULT_NAME, DOMAIN


class IntexPureSpaEntity(CoordinatorEntity[IntexPureSpaCoordinator]):
    """Base class for all Intex PureSpa entities."""

    def __init__(
        self,
        coordinator: IntexPureSpaCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entry = entry
        self._spa_name: str = entry.data.get("name", DEFAULT_NAME)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for the spa."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.device_id)},
            name=self._spa_name,
            manufacturer="Intex",
            model="PureSpa (Tuya)",
        )

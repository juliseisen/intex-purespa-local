"""Intex PureSpa (Tuya Local) integration for Home Assistant.

Controls Tuya-based Intex PureSpa models ("TY" control panels) directly
over the local network (TCP port 6668), without any cloud dependency at
runtime. A persistent connection receives instant push updates, so
changes made on the spa's control panel appear immediately.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    EVENT_HOMEASSISTANT_STOP,
    UnitOfTemperature,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import IntexPureSpaMonitor
from .const import (
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL_VERSION,
    DOMAIN,
    DP_TARGET_TEMP,
    FAHRENHEIT_DETECTION_THRESHOLD,
    PLATFORMS,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)

# Seconds to wait for the first status push after connecting
FIRST_DATA_TIMEOUT = 20


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Intex PureSpa from a config entry."""
    coordinator = IntexPureSpaCoordinator(hass, entry)
    coordinator.monitor.start()

    try:
        async with asyncio.timeout(FIRST_DATA_TIMEOUT):
            await coordinator.first_data.wait()
    except TimeoutError as err:
        await hass.async_add_executor_job(coordinator.monitor.stop)
        raise ConfigEntryNotReady(
            f"No response from the spa at {entry.data[CONF_HOST]}"
        ) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async def _async_stop_monitor(_: Event) -> None:
        await hass.async_add_executor_job(coordinator.monitor.stop)

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop_monitor)
    )

    return True


class IntexPureSpaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Push-based coordinator fed by the persistent spa connection."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator and its monitor thread."""
        self.device_id: str = entry.data[CONF_DEVICE_ID]
        # The spa often pushes partial dps updates, so merge every
        # update into the last known full state
        self._merged_dps: dict[str, Any] = {}
        self.first_data = asyncio.Event()

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            # Push-based: the monitor thread delivers updates, there is
            # no polling schedule
            update_interval=None,
        )

        self.monitor = IntexPureSpaMonitor(
            host=entry.data[CONF_HOST],
            device_id=entry.data[CONF_DEVICE_ID],
            local_key=entry.data[CONF_LOCAL_KEY],
            version=entry.data[CONF_PROTOCOL_VERSION],
            on_dps=self._threadsafe_dps,
            on_disconnect=self._threadsafe_disconnect,
        )

    def _threadsafe_dps(self, dps: dict[str, Any]) -> None:
        """Forward pushed data points into the event loop (thread-safe)."""
        self.hass.loop.call_soon_threadsafe(self._handle_dps, dict(dps))

    def _threadsafe_disconnect(self, message: str) -> None:
        """Forward a connection loss into the event loop (thread-safe)."""
        self.hass.loop.call_soon_threadsafe(self._handle_disconnect, message)

    @callback
    def _handle_dps(self, dps: dict[str, Any]) -> None:
        """Merge pushed data points and notify all entities."""
        self._merged_dps.update(dps)
        self.first_data.set()
        self.async_set_updated_data(dict(self._merged_dps))

    @callback
    def _handle_disconnect(self, message: str) -> None:
        """Mark all entities unavailable after a connection loss."""
        self.async_set_update_error(UpdateFailed(message))

    @property
    def temperature_unit(self) -> str:
        """Return the temperature unit the spa reports in.

        The spa reports plain numbers: 20-40 when set to Celsius,
        68-104 when set to Fahrenheit. The ranges do not overlap.
        """
        target = (self.data or {}).get(DP_TARGET_TEMP)
        if (
            isinstance(target, (int, float))
            and target > FAHRENHEIT_DETECTION_THRESHOLD
        ):
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS

    async def async_set_dp(self, dp: str, value: Any) -> None:
        """Queue a data point write and update the state optimistically.

        The spa confirms the change with a push message within about a
        second; the periodic full query corrects any drift.
        """
        if not self.monitor.connected.is_set():
            raise HomeAssistantError("The spa is currently not reachable")
        self.monitor.queue_command(dp, value)
        self._handle_dps({dp: value})


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: IntexPureSpaCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(coordinator.monitor.stop)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)

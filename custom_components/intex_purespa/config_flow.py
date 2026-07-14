"""Config flow for the Intex PureSpa (Tuya Local) integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .api import IntexPureSpaApi, IntexPureSpaApiError
from .const import (
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL_VERSION,
    DEFAULT_NAME,
    DOMAIN,
    PROTOCOL_VERSION_AUTO,
    PROTOCOL_VERSIONS,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_LOCAL_KEY): cv.string,
        vol.Optional(CONF_PROTOCOL_VERSION, default=PROTOCOL_VERSION_AUTO): vol.In(
            [PROTOCOL_VERSION_AUTO, *PROTOCOL_VERSIONS]
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> str:
    """Try to reach the spa and return the working protocol version."""
    requested = data[CONF_PROTOCOL_VERSION]
    versions = (
        PROTOCOL_VERSIONS if requested == PROTOCOL_VERSION_AUTO else [requested]
    )

    last_error: IntexPureSpaApiError | None = None
    for version in versions:
        api = IntexPureSpaApi(
            host=data[CONF_HOST],
            device_id=data[CONF_DEVICE_ID],
            local_key=data[CONF_LOCAL_KEY],
            version=version,
        )
        try:
            dps = await hass.async_add_executor_job(api.status)
        except IntexPureSpaApiError as err:
            _LOGGER.debug(
                "Protocol version %s failed: %s (code %s)",
                version,
                err,
                err.code,
            )
            last_error = err
            if err.is_network_error:
                # The device is unreachable, trying other protocol
                # versions will not help
                raise CannotConnect from err
            continue

        _LOGGER.debug("Protocol version %s works, dps: %s", version, dps)
        return version

    raise InvalidKey from last_error


class IntexPureSpaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow to add an Intex PureSpa."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            try:
                version = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors[CONF_HOST] = "cannot_connect"
            except InvalidKey:
                errors[CONF_LOCAL_KEY] = "invalid_key"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, DEFAULT_NAME),
                    data={**user_input, CONF_PROTOCOL_VERSION: version},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """The spa is not reachable on the network."""


class InvalidKey(HomeAssistantError):
    """The spa is reachable but rejects the local key."""

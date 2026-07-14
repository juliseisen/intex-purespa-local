"""Local Tuya connection handling for the Intex PureSpa.

Two access paths:

- ``IntexPureSpaApi``: one-shot, blocking status read. Used by the
  config flow to validate the connection settings.
- ``IntexPureSpaMonitor``: a background thread that owns one persistent
  connection to the spa. The spa's wifi module only accepts a single
  local client, so all traffic (status pushes from panel changes,
  heartbeats, periodic full queries and outgoing commands) runs over
  this one socket, touched exclusively by this thread.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from typing import Any

import tinytuya

_LOGGER: logging.Logger = logging.getLogger(__package__)

# Seconds between keep-alive heartbeats (module drops idle connections
# after roughly 15 seconds)
HEARTBEAT_INTERVAL = 8.0
# Seconds between full DP_QUERY polls (safety net in case a push is missed)
FULL_QUERY_INTERVAL = 30.0
# Socket receive timeout; also the worst-case latency for queued commands
RECEIVE_TIMEOUT = 1.0
# Seconds to wait before reconnecting after a lost connection
RECONNECT_DELAY = 10.0
# TCP connect timeout for new sessions
CONNECT_TIMEOUT = 8

# tinytuya error codes that indicate the device is unreachable on the
# network (as opposed to a wrong local key / protocol version)
NETWORK_ERROR_CODES = {"901", "902", "905"}
# Waiting for data ran into the receive timeout - no data, not an error
TIMEOUT_ERROR_CODE = "902"


class IntexPureSpaApiError(Exception):
    """Raised when the spa cannot be reached or returns an error."""

    def __init__(self, message: str, code: str | None = None) -> None:
        """Initialize with message and optional tinytuya error code."""
        super().__init__(message)
        self.code = code

    @property
    def is_network_error(self) -> bool:
        """Return True if the error looks like a connectivity problem."""
        return self.code in NETWORK_ERROR_CODES


def _create_device(
    host: str, device_id: str, local_key: str, version: str
) -> tinytuya.Device:
    """Create a configured tinytuya device."""
    device = tinytuya.Device(
        device_id,
        host,
        local_key,
        connection_timeout=CONNECT_TIMEOUT,
    )
    device.set_version(float(version))
    device.set_socketRetryLimit(1)
    return device


class IntexPureSpaApi:
    """One-shot blocking access, used by the config flow."""

    def __init__(
        self, host: str, device_id: str, local_key: str, version: str
    ) -> None:
        """Initialize the api wrapper."""
        self._host = host
        self._device_id = device_id
        self._local_key = local_key
        self.version = version

    def status(self) -> dict[str, Any]:
        """Read the current status (all data points) from the spa."""
        device = _create_device(
            self._host, self._device_id, self._local_key, self.version
        )
        device.set_socketTimeout(CONNECT_TIMEOUT)
        try:
            result = device.status()
        finally:
            device.close()

        if not isinstance(result, dict):
            raise IntexPureSpaApiError(f"Unexpected response: {result!r}")
        if "Error" in result:
            raise IntexPureSpaApiError(
                str(result.get("Error")), code=str(result.get("Err"))
            )
        dps = result.get("dps")
        if not isinstance(dps, dict):
            raise IntexPureSpaApiError(f"Response without dps: {result!r}")
        return dps


class IntexPureSpaMonitor(threading.Thread):
    """Background thread with a persistent connection to the spa.

    Status updates (including changes made on the spa's control panel)
    are pushed by the device over the open socket and forwarded via the
    ``on_dps`` callback. Commands are queued with ``queue_command`` and
    sent by this thread, so no other thread ever touches the socket.
    """

    def __init__(
        self,
        host: str,
        device_id: str,
        local_key: str,
        version: str,
        on_dps: Callable[[dict[str, Any]], None],
        on_disconnect: Callable[[str], None],
    ) -> None:
        """Initialize the monitor thread."""
        super().__init__(name=f"IntexPureSpa-{host}", daemon=True)
        self._host = host
        self._device_id = device_id
        self._local_key = local_key
        self._version = version
        self._on_dps = on_dps
        self._on_disconnect = on_disconnect
        self._commands: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._stop_event = threading.Event()
        self.connected = threading.Event()

    def queue_command(self, dp: str, value: Any) -> None:
        """Queue one data point write; sent within ~1 second."""
        self._commands.put((dp, value))

    def stop(self) -> None:
        """Stop the thread and wait for it to finish (blocking)."""
        self._stop_event.set()
        if self.is_alive():
            self.join(timeout=15)

    def run(self) -> None:
        """Keep one session open, reconnect with delay on failure."""
        while not self._stop_event.is_set():
            error_message = "Connection lost"
            try:
                self._session()
            except IntexPureSpaApiError as err:
                error_message = str(err)
                _LOGGER.debug("Spa session ended: %s", err)
            except Exception as err:  # pylint: disable=broad-except
                error_message = str(err)
                _LOGGER.exception("Unexpected error in spa session")

            self.connected.clear()
            if not self._stop_event.is_set():
                self._on_disconnect(error_message)
                self._stop_event.wait(RECONNECT_DELAY)

    def _session(self) -> None:
        """Run one persistent connection until it fails or we stop."""
        device = _create_device(
            self._host, self._device_id, self._local_key, self._version
        )
        device.set_socketPersistent(True)
        device.set_socketTimeout(RECEIVE_TIMEOUT)
        try:
            # Initial full status request; this also opens the socket
            # (including the session handshake on protocol 3.4/3.5)
            device.send(device.generate_payload(tinytuya.DP_QUERY))
            self.connected.set()
            last_heartbeat = last_query = time.monotonic()

            while not self._stop_event.is_set():
                payload = device.receive()
                self._handle_payload(payload)

                self._drain_commands(device)

                now = time.monotonic()
                if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    device.send(device.generate_payload(tinytuya.HEART_BEAT))
                    last_heartbeat = now
                if now - last_query >= FULL_QUERY_INTERVAL:
                    device.send(device.generate_payload(tinytuya.DP_QUERY))
                    last_query = now
        finally:
            self.connected.clear()
            device.close()

    def _handle_payload(self, payload: Any) -> None:
        """Extract data points from a received payload and forward them."""
        if not payload or not isinstance(payload, dict):
            # None / empty dict: receive timeout or heartbeat ack
            return

        if "Error" in payload:
            code = str(payload.get("Err"))
            if code == TIMEOUT_ERROR_CODE:
                return  # no data within the receive timeout - normal
            raise IntexPureSpaApiError(str(payload.get("Error")), code=code)

        dps = payload.get("dps")
        if dps is None and isinstance(payload.get("data"), dict):
            dps = payload["data"].get("dps")

        if isinstance(dps, dict) and dps:
            _LOGGER.debug("Spa pushed dps: %s", dps)
            self._on_dps(dps)

    def _drain_commands(self, device: tinytuya.Device) -> None:
        """Send all queued commands over the open socket."""
        while True:
            try:
                dp, value = self._commands.get_nowait()
            except queue.Empty:
                return
            _LOGGER.debug("Sending dp %s = %s", dp, value)
            try:
                device.send(device.generate_payload(tinytuya.CONTROL, {dp: value}))
            except Exception as err:
                _LOGGER.warning(
                    "Command dp %s = %s failed, connection is restarted: %s",
                    dp,
                    value,
                    err,
                )
                raise

"""TCP client for Shure wireless receivers using their network string protocol."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 2202
METER_RATE_MS = 30000  # Request metering updates every 30 seconds


@dataclass
class ChannelState:
    """State for a single receiver channel."""

    name: str = ""
    frequency: str = ""
    audio_level: int = -120  # dBFS
    audio_level_peak: int = -120  # dBFS
    rf_level: int = -120  # dBm
    antenna: str = "XX"
    battery_bars: int | None = None  # 1-5, 255=unknown
    battery_charge: int | None = None  # percent, 255=unknown
    battery_runtime: int | None = None  # minutes, 65535=unknown
    battery_type: str = ""
    battery_health: int | None = None  # percent
    battery_cycle: int | None = None
    battery_temp_c: int | None = None
    tx_model: str = ""
    tx_device_id: str = ""
    tx_mute_status: str = ""
    audio_gain: int | None = None
    audio_mute: str = ""
    interference_status: str = ""
    encryption_status: str = ""


@dataclass
class ReceiverState:
    """State for the receiver device."""

    device_id: str = ""
    firmware_version: str = ""
    model: str = ""
    rf_band: str = ""
    encryption: str = ""
    lock_status: str = ""


class ShureClient:
    """Async TCP client for Shure wireless receivers.

    Protocol: Commands are wrapped in angle brackets: < CMD >
    Responses come as: < REP ... > or < SAMPLE ... >
    Port 2202 by default.
    """

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        num_channels: int = 4,
    ) -> None:
        """Initialize the client."""
        self.host = host
        self.port = port
        self.num_channels = num_channels

        self.receiver = ReceiverState()
        self.channels: dict[int, ChannelState] = {i: ChannelState() for i in range(1, num_channels + 1)}

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._listen_task: asyncio.Task | None = None
        self._connected = False
        self._update_callbacks: list[Callable[[], None]] = []
        self._buffer = ""

    @property
    def connected(self) -> bool:
        """Return True if connected."""
        return self._connected

    def register_callback(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a callback for state updates. Returns unregister function."""
        self._update_callbacks.append(callback)

        def unregister() -> None:
            self._update_callbacks.remove(callback)

        return unregister

    def _notify_update(self) -> None:
        """Notify all registered callbacks."""
        for callback in self._update_callbacks:
            try:
                callback()
            except Exception:
                _LOGGER.exception("Error in update callback")

    async def connect(self) -> None:
        """Connect to the receiver."""
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=10,
        )
        self._connected = True
        self._listen_task = asyncio.create_task(self._listen())

        # Request receiver-level state
        for prop in ("MODEL", "FW_VER", "DEVICE_ID", "RF_BAND", "ENCRYPTION"):
            await self.send_command(f"GET {prop}")

        # Request per-channel state (GET 0 ALL is not supported on SLXD4D+)
        channel_props = (
            "CHAN_NAME",
            "FREQUENCY",
            "AUDIO_GAIN",
            "AUDIO_MUTE",
            "TX_TYPE",
            "TX_DEVICE_ID",
            "TX_BATT_MINS",
            "TX_BATT_BARS",
            "BATT_TYPE",
            "ENCRYPTION",
        )
        for ch in range(1, self.num_channels + 1):
            for prop in channel_props:
                await self.send_command(f"GET {ch} {prop}")

        # Enable metering for sample data (RF/audio levels)
        await self.send_command(f"SET 0 METER_RATE {METER_RATE_MS}")

    async def disconnect(self) -> None:
        """Disconnect from the receiver."""
        self._connected = False
        if self._listen_task:
            self._listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listen_task
            self._listen_task = None
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def send_command(self, cmd: str) -> None:
        """Send a command to the receiver."""
        if self._writer is None:
            raise ConnectionError("Not connected")
        message = f"< {cmd} >"
        _LOGGER.debug("Sending: %s", message)
        self._writer.write(message.encode("ascii"))
        await self._writer.drain()

    async def _listen(self) -> None:
        """Listen for data from the receiver."""
        try:
            while self._connected and self._reader:
                data = await self._reader.read(4096)
                if not data:
                    _LOGGER.warning("Connection closed by receiver")
                    self._connected = False
                    self._notify_update()
                    break
                self._buffer += data.decode("ascii", errors="replace")
                self._process_buffer()
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Error in listener")
            self._connected = False
            self._notify_update()

    def _process_buffer(self) -> None:
        """Process buffered data, extracting complete messages."""
        offset = 0
        while True:
            end = self._buffer.find(">", offset)
            if end == -1:
                break
            start = self._buffer.rfind("<", offset, end)
            if start != -1:
                line = self._buffer[start + 1 : end].strip()
                self._process_line(line)
            offset = end + 1
        self._buffer = self._buffer[offset:]

    def _process_line(self, line: str) -> None:
        """Process a single response line from the receiver."""
        _LOGGER.debug("Received: %s", line)
        parts = line.split()
        if len(parts) < 2:
            return

        command_type = parts[0]

        if command_type == "REP":
            self._process_rep(parts[1:])
        elif command_type == "SAMPLE":
            self._process_sample(parts[1:])

    def _process_rep(self, parts: list[str]) -> None:
        """Process a REP (report) response."""
        if len(parts) < 2:
            return

        # Try to parse channel number
        try:
            channel_num = int(parts[0])
        except ValueError:
            # Receiver-level property
            key = parts[0]
            value = " ".join(parts[1:])
            self._update_receiver(key, value)
            self._notify_update()
            return

        if len(parts) < 3:
            return

        key = parts[1]
        value = " ".join(parts[2:])
        self._update_channel(channel_num, key, value)
        self._notify_update()

    def _process_sample(self, parts: list[str]) -> None:
        """Process a SAMPLE (metering) response.

        SLXD format: SAMPLE <ch> ALL <rf_level> <audio_peak> <audio_rms>
        Indices after removing SAMPLE: [0]=ch [1]=ALL [2]=rf [3]=audio_peak [4]=audio_rms
        """
        if len(parts) < 5:
            return

        try:
            channel_num = int(parts[0])
        except ValueError:
            return

        channel = self.channels.get(channel_num)
        if channel is None:
            return

        try:
            channel.rf_level = int(parts[2]) - 120
            channel.audio_level_peak = int(parts[3]) - 120
            channel.audio_level = int(parts[4]) - 120
        except (ValueError, IndexError):
            _LOGGER.debug("Failed to parse SAMPLE data: %s", parts)
            return

        self._notify_update()

    def _clean_value(self, value: str) -> str:
        """Remove braces and trim whitespace from a value."""
        return value.replace("{", "").replace("}", "").strip()

    def _update_receiver(self, key: str, value: str) -> None:
        """Update receiver-level state."""
        value = self._clean_value(value)

        if key == "FW_VER":
            self.receiver.firmware_version = value
        elif key == "DEVICE_ID":
            self.receiver.device_id = value
        elif key == "MODEL":
            self.receiver.model = value
        elif key == "RF_BAND":
            self.receiver.rf_band = value
        elif key == "ENCRYPTION":
            self.receiver.encryption = value
        elif key == "LOCK_STATUS":
            self.receiver.lock_status = value

    def _update_channel(self, channel_num: int, key: str, value: str) -> None:
        """Update channel-level state."""
        channel = self.channels.get(channel_num)
        if channel is None:
            return

        cleaned = self._clean_value(value)

        if key == "CHAN_NAME":
            channel.name = cleaned
        elif key == "FREQUENCY":
            raw = str(int(value))
            channel.frequency = raw[:3] + "." + raw[3:6]
        elif key == "AUDIO_GAIN":
            channel.audio_gain = int(value) - 18
        elif key == "AUDIO_MUTE":
            channel.audio_mute = value
        elif key in ("TX_TYPE", "TX_MODEL"):
            channel.tx_model = value
        elif key == "TX_DEVICE_ID":
            channel.tx_device_id = cleaned
        elif key in ("BATT_BARS", "TX_BATT_BARS"):
            val = int(value)
            channel.battery_bars = None if val == 255 else val
        elif key == "BATT_CHARGE":
            val = int(value)
            channel.battery_charge = None if val == 255 else val
        elif key in ("TX_BATT_MINS", "BATT_RUN_TIME"):
            val = int(value)
            channel.battery_runtime = None if val >= 65533 else val
        elif key == "BATT_TYPE":
            channel.battery_type = value
        elif key == "BATT_HEALTH":
            val = int(value)
            channel.battery_health = None if val == 255 else val
        elif key == "BATT_CYCLE":
            val = int(value)
            channel.battery_cycle = None if val == 65535 else val
        elif key == "BATT_TEMP_C":
            val = int(value)
            channel.battery_temp_c = None if val == 255 else val + 40
        elif key in ("RF_INT_DET", "INTERFERENCE_STATUS"):
            channel.interference_status = "DETECTED" if value == "CRITICAL" else value
        elif key == "ENCRYPTION":
            channel.encryption_status = "OK" if value == "OFF" else value
        elif key in ("MUTE_STATUS", "MUTE_MODE_STATUS"):
            if value == "ON":
                channel.tx_mute_status = "OFF"
            elif value == "MUTE":
                channel.tx_mute_status = "ON"
            else:
                channel.tx_mute_status = value

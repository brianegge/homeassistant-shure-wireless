"""ACN Service Location Protocol discovery for Shure wireless receivers.

Shure SLXD receivers announce themselves via ESTA E1.17 (ACN) multicast
on 239.255.254.253:8427. This module listens for those announcements and
triggers Home Assistant config flows for discovered devices.
"""

from __future__ import annotations

import asyncio
import logging
import re
import socket
import struct
from dataclasses import dataclass

import ifaddr
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

ACN_MULTICAST_GROUP = "239.255.254.253"
ACN_PORT = 8427

# Model name to channel count mapping
_CHANNEL_COUNT = {
    "SLXD4": 1,
    "SLXD4D": 2,
    "SLXD4DE": 2,
}


@dataclass
class ShureDeviceInfo:
    """Discovered Shure device information."""

    host: str
    model: str
    name: str
    cid: str
    num_channels: int


def _parse_acn_announcement(data: bytes, source_addr: str) -> ShureDeviceInfo | None:
    """Parse an ACN SLP multicast announcement into device info."""
    try:
        text = data.decode("ascii", errors="replace")
    except Exception:
        return None

    fields: dict[str, str] = {}
    for match in re.finditer(r"\(([^=]+)=([^)]*)\)", text):
        fields[match.group(1)] = match.group(2)

    function = fields.get("acn-fctn", "")
    if not function:
        return None

    # Only discover actual receivers, not utilities like the Shure Updater
    if "_RX" not in function:
        return None

    # Extract model from function name (e.g. "SLXD4DE_RX" -> "SLXD4DE")
    model = function.replace("_RX", "")

    # Determine channel count from model
    num_channels = 1
    for prefix in sorted(_CHANNEL_COUNT, key=len, reverse=True):
        if model.startswith(prefix):
            num_channels = _CHANNEL_COUNT[prefix]
            break

    user_name = fields.get("acn-uacn", model)
    cid = fields.get("cid", "")

    return ShureDeviceInfo(
        host=source_addr,
        model=model,
        name=user_name,
        cid=cid,
        num_channels=num_channels,
    )


class ShureDiscoveryProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for ACN multicast discovery."""

    def __init__(self, callback: asyncio.Future | None = None) -> None:
        """Initialize."""
        self._devices: dict[str, ShureDeviceInfo] = {}
        self._callbacks: list[callable] = []
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        """Handle connection made."""
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Handle received datagram."""
        source_ip = addr[0]
        device = _parse_acn_announcement(data, source_ip)
        if device is None:
            return

        key = device.cid or source_ip
        is_new = key not in self._devices
        self._devices[key] = device

        if is_new:
            _LOGGER.info(
                "Discovered Shure %s (%s) at %s",
                device.model,
                device.name,
                device.host,
            )
        for callback in self._callbacks:
            try:
                callback(device, is_new)
            except Exception:
                _LOGGER.exception("Error in discovery callback")

    def register_callback(self, callback: callable) -> None:
        """Register a callback for device discovery."""
        self._callbacks.append(callback)

    @property
    def devices(self) -> dict[str, ShureDeviceInfo]:
        """Return discovered devices."""
        return dict(self._devices)


async def create_discovery_listener(
    hass: HomeAssistant,
) -> tuple[asyncio.DatagramTransport, ShureDiscoveryProtocol]:
    """Create and start the ACN multicast discovery listener."""
    loop = hass.loop

    # Create a UDP socket for multicast
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(("", ACN_PORT))

    # Join the multicast group on every IPv4 interface
    group = socket.inet_aton(ACN_MULTICAST_GROUP)
    joined = 0
    for adapter in ifaddr.get_adapters():
        for ip in adapter.ips:
            if not isinstance(ip.ip, str):
                continue  # skip IPv6
            if ip.ip.startswith("127."):
                continue
            try:
                mreq = struct.pack("4s4s", group, socket.inet_aton(ip.ip))
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                joined += 1
                _LOGGER.debug("Joined ACN multicast on %s (%s)", adapter.nice_name, ip.ip)
            except OSError as err:
                _LOGGER.debug("Could not join multicast on %s: %s", ip.ip, err)
    if joined == 0:
        # Fallback to INADDR_ANY
        mreq = struct.pack("4sL", group, socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.setblocking(False)

    transport, protocol = await loop.create_datagram_endpoint(
        ShureDiscoveryProtocol,
        sock=sock,
    )

    return transport, protocol

"""
RCON client for communicating with a Minecraft Paper server.
Implements the Source RCON protocol (same as used by Valve / Minecraft).
"""

from __future__ import annotations

import socket
import struct
import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)

_AUTH         = 3
_AUTH_RESP    = 2
_COMMAND      = 2
_COMMAND_RESP = 0

_PACKET_ID = 1


class RCONError(Exception):
    """Raised when RCON communication fails."""


class RCONClient:
    def __init__(
        self,
        host: str = config.RCON_HOST,
        port: int = config.RCON_PORT,
        password: str = config.RCON_PASSWORD,
        timeout: float = 10.0,
    ) -> None:
        self._host = host
        self._port = port
        self._password = password
        self._timeout = timeout
        self._sock: Optional[socket.socket] = None

    def __enter__(self) -> "RCONClient":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.disconnect()

    def connect(self) -> None:
        self._sock = socket.create_connection(
            (self._host, self._port), timeout=self._timeout
        )
        self._send(_AUTH, self._password)
        pkt_id, pkt_type, _ = self._recv()
        if pkt_id == -1 or pkt_type != _AUTH_RESP:
            raise RCONError("RCON authentication failed — wrong password?")

    def disconnect(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _send(self, pkt_type: int, payload: str) -> None:
        data = payload.encode("utf-8") + b"\x00\x00"
        header = struct.pack("<iii", len(data) + 8, _PACKET_ID, pkt_type)
        self._sock.sendall(header + data)

    def _recv(self) -> tuple[int, int, str]:
        raw_len = self._recv_exactly(4)
        (length,) = struct.unpack("<i", raw_len)
        payload = self._recv_exactly(length)
        pkt_id, pkt_type = struct.unpack("<ii", payload[:8])
        body = payload[8:].rstrip(b"\x00").decode("utf-8", errors="replace")
        return pkt_id, pkt_type, body

    def _recv_exactly(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise RCONError("Connection closed by server")
            buf += chunk
        return buf

    def send_command(self, command: str) -> str:
        if not self._sock:
            raise RCONError("Not connected")
        self._send(_COMMAND, command)
        _, _, response = self._recv()
        logger.debug("RCON ← %s", response)
        return response


def grant_rank(ign: str, luckperms_group: str) -> str:
    command = f"lp user {ign} parent set {luckperms_group}"
    logger.info("Sending RCON command: %s", command)
    with RCONClient() as client:
        response = client.send_command(command)
    logger.info("RCON response: %s", response)
    return response


def revoke_rank(ign: str, luckperms_group: str) -> str:
    command = f"lp user {ign} parent remove {luckperms_group}"
    logger.info("Sending RCON command: %s", command)
    with RCONClient() as client:
        response = client.send_command(command)
    logger.info("RCON response: %s", response)
    return response

from __future__ import annotations

import asyncio
import itertools
import struct
from dataclasses import dataclass


SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0


class RconError(RuntimeError):
    pass


@dataclass(frozen=True)
class RconClient:
    host: str
    port: int
    password: str
    timeout_seconds: float = 5

    async def execute(self, command: str) -> str:
        if not self.password:
            raise RconError("MC_RCON_PASSWORD is required for whitelist reload")

        reader: asyncio.StreamReader
        writer: asyncio.StreamWriter
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=self.timeout_seconds,
        )

        request_ids = itertools.count(1)
        try:
            auth_id = next(request_ids)
            await self._write_packet(writer, auth_id, SERVERDATA_AUTH, self.password)
            response_id, response_type, _ = await self._read_packet(reader)
            if response_id == -1 or response_type != SERVERDATA_AUTH_RESPONSE:
                raise RconError("RCON authentication failed")

            command_id = next(request_ids)
            await self._write_packet(writer, command_id, SERVERDATA_EXECCOMMAND, command)
            response_id, response_type, payload = await self._read_packet(reader)
            if response_id != command_id or response_type not in {
                SERVERDATA_RESPONSE_VALUE,
                SERVERDATA_AUTH_RESPONSE,
            }:
                raise RconError("Unexpected RCON response")
            return payload
        finally:
            writer.close()
            await writer.wait_closed()

    async def _write_packet(
        self,
        writer: asyncio.StreamWriter,
        request_id: int,
        request_type: int,
        payload: str,
    ) -> None:
        payload_bytes = payload.encode("utf-8")
        packet = (
            struct.pack("<iii", len(payload_bytes) + 10, request_id, request_type)
            + payload_bytes
            + b"\x00\x00"
        )
        writer.write(packet)
        await writer.drain()

    async def _read_packet(self, reader: asyncio.StreamReader) -> tuple[int, int, str]:
        header = await asyncio.wait_for(reader.readexactly(4), timeout=self.timeout_seconds)
        (packet_length,) = struct.unpack("<i", header)
        if packet_length < 10:
            raise RconError("Invalid RCON packet length")
        body = await asyncio.wait_for(
            reader.readexactly(packet_length),
            timeout=self.timeout_seconds,
        )
        request_id, response_type = struct.unpack("<ii", body[:8])
        payload = body[8:-2].decode("utf-8", errors="replace")
        return request_id, response_type, payload

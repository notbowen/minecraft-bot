from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from ipaddress import ip_address
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class PublicIpError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConnectInfo:
    ip: str
    port: int

    @property
    def address(self) -> str:
        parsed = ip_address(self.ip)
        if parsed.version == 6:
            return f"[{self.ip}]:{self.port}"
        return f"{self.ip}:{self.port}"


def fetch_public_ip(url: str, *, timeout_seconds: float = 5) -> str:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "minecraft-discord-bot",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw_body = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError, socket.timeout) as error:
        raise PublicIpError(f"Could not fetch public IP from {url}") from error

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise PublicIpError(f"{url} did not return JSON") from error

    ip = payload.get("ip")
    if not isinstance(ip, str):
        raise PublicIpError(f"{url} response did not include an IP address")

    try:
        return str(ip_address(ip.strip()))
    except ValueError as error:
        raise PublicIpError(f"{url} returned an invalid IP address") from error

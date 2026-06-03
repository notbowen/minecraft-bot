from __future__ import annotations

from minecraft_bot.connect import ConnectInfo


def test_connect_info_formats_ipv4_with_port() -> None:
    assert ConnectInfo(ip="203.0.113.10", port=25565).address == "203.0.113.10:25565"


def test_connect_info_formats_ipv6_with_brackets() -> None:
    assert ConnectInfo(ip="2001:db8::1", port=25565).address == "[2001:db8::1]:25565"

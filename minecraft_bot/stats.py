from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StatSummary:
    overview: str
    top_mined: str
    top_crafted: str
    top_killed: str
    top_used: str


def summarize_stats(data: dict[str, Any]) -> StatSummary:
    stats = data.get("stats", {})
    if not isinstance(stats, dict):
        stats = {}

    custom = _stat_group(stats, "minecraft:custom")
    overview_lines = [
        f"Playtime: {_format_ticks(custom.get('minecraft:play_time', 0))}",
        f"Deaths: {custom.get('minecraft:deaths', 0):,}",
        f"Mob kills: {custom.get('minecraft:mob_kills', 0):,}",
        f"Player kills: {custom.get('minecraft:player_kills', 0):,}",
        f"Jumps: {custom.get('minecraft:jump', 0):,}",
        f"Distance: {_format_distance(total_distance_cm(custom))}",
    ]

    return StatSummary(
        overview="\n".join(overview_lines),
        top_mined=_format_top(_stat_group(stats, "minecraft:mined")) or "No blocks mined yet.",
        top_crafted=_format_top(_stat_group(stats, "minecraft:crafted")) or "No items crafted yet.",
        top_killed=_format_top(_stat_group(stats, "minecraft:killed")) or "No mobs killed yet.",
        top_used=_format_top(_stat_group(stats, "minecraft:used")) or "No item usage yet.",
    )


def total_distance_cm(custom: dict[str, int]) -> int:
    keys = (
        "minecraft:walk_one_cm",
        "minecraft:sprint_one_cm",
        "minecraft:crouch_one_cm",
        "minecraft:swim_one_cm",
        "minecraft:fall_one_cm",
        "minecraft:climb_one_cm",
        "minecraft:fly_one_cm",
        "minecraft:boat_one_cm",
        "minecraft:horse_one_cm",
        "minecraft:minecart_one_cm",
        "minecraft:walk_on_water_one_cm",
        "minecraft:walk_under_water_one_cm",
    )
    return sum(int(custom.get(key, 0)) for key in keys)


def _stat_group(stats: dict[str, Any], group: str) -> dict[str, int]:
    raw = stats.get(group, {})
    if not isinstance(raw, dict):
        return {}
    result: dict[str, int] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, int):
            result[key] = value
    return result


def _format_ticks(ticks: int) -> str:
    seconds = int(ticks) // 20
    minutes, _ = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)


def _format_distance(cm: int) -> str:
    meters = int(cm) / 100
    if meters >= 1000:
        return f"{meters / 1000:,.1f} km"
    return f"{meters:,.0f} m"


def _format_top(values: dict[str, int], *, limit: int = 5) -> str:
    lines = []
    for key, value in sorted(values.items(), key=lambda item: item[1], reverse=True)[:limit]:
        lines.append(f"{_format_identifier(key)}: {value:,}")
    return "\n".join(lines)


def _format_identifier(identifier: str) -> str:
    namespace, _, path = identifier.partition(":")
    if not path:
        path = namespace
        namespace = "minecraft"
    label = path.replace("_", " ").replace("/", " ").title()
    if namespace and namespace != "minecraft":
        return f"{label} ({namespace})"
    return label

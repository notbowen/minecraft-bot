from __future__ import annotations

from minecraft_bot.stats import summarize_stats


def test_summarize_stats_formats_overview_and_top_sections() -> None:
    summary = summarize_stats(
        {
            "stats": {
                "minecraft:custom": {
                    "minecraft:play_time": 72_000,
                    "minecraft:deaths": 2,
                    "minecraft:mob_kills": 7,
                    "minecraft:jump": 42,
                    "minecraft:walk_one_cm": 123_456,
                },
                "minecraft:mined": {"minecraft:stone": 15, "create:andesite_casing": 3},
                "minecraft:crafted": {"minecraft:torch": 64},
                "minecraft:killed": {"minecraft:zombie": 5},
                "minecraft:used": {"minecraft:diamond_pickaxe": 21},
            }
        }
    )

    assert "Playtime: 1h" in summary.overview
    assert "Deaths: 2" in summary.overview
    assert "Distance: 1.2 km" in summary.overview
    assert "Stone: 15" in summary.top_mined
    assert "Andesite Casing (create): 3" in summary.top_mined

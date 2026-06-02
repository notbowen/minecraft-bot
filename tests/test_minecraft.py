from __future__ import annotations

import json

from minecraft_bot.minecraft import MinecraftData, offline_uuid


def test_offline_uuid_matches_existing_server_users() -> None:
    assert str(offline_uuid("wHo6933")) == "001fe3f0-9f9b-3257-a003-3f3a70fdfef9"
    assert str(offline_uuid("PotatoSalad")) == "db34e03e-7933-3bdf-bafa-22a1431b8881"
    assert str(offline_uuid("fullerz")) == "64873c95-d31c-3859-9c6e-e832167a656f"


def test_add_to_whitelist_updates_blank_existing_uuid(tmp_path) -> None:
    data_dir = tmp_path
    whitelist_path = data_dir / "whitelist.json"
    whitelist_path.write_text(
        json.dumps([{"name": "", "uuid": str(offline_uuid("fullerz"))}]),
        encoding="utf-8",
    )

    result = MinecraftData(data_dir).add_to_whitelist("fullerz")

    assert result.action == "updated"
    assert json.loads(whitelist_path.read_text(encoding="utf-8")) == [
        {"name": "fullerz", "uuid": str(offline_uuid("fullerz"))}
    ]


def test_add_to_whitelist_appends_new_user(tmp_path) -> None:
    whitelist_path = tmp_path / "whitelist.json"
    whitelist_path.write_text("[]", encoding="utf-8")

    result = MinecraftData(tmp_path).add_to_whitelist("Steve")

    assert result.action == "added"
    assert json.loads(whitelist_path.read_text(encoding="utf-8")) == [
        {"uuid": "5627dd98-e6be-3c21-b8a8-e92344183641", "name": "Steve"}
    ]


def test_remove_from_whitelist_removes_by_stored_uuid_and_name(tmp_path) -> None:
    whitelist_path = tmp_path / "whitelist.json"
    old_uuid = str(offline_uuid("OldName"))
    whitelist_path.write_text(
        json.dumps(
            [
                {"uuid": old_uuid, "name": "OldName"},
                {"uuid": str(offline_uuid("Alex")), "name": "Alex"},
            ]
        ),
        encoding="utf-8",
    )

    result = MinecraftData(tmp_path).remove_from_whitelist("OldName", old_uuid)

    assert result.action == "removed"
    assert json.loads(whitelist_path.read_text(encoding="utf-8")) == [
        {"uuid": str(offline_uuid("Alex")), "name": "Alex"}
    ]


def test_list_players_uses_caches_and_stats(tmp_path) -> None:
    (tmp_path / "world" / "stats").mkdir(parents=True)
    (tmp_path / "usernamecache.json").write_text(
        json.dumps({"001fe3f0-9f9b-3257-a003-3f3a70fdfef9": "wHo6933"}),
        encoding="utf-8",
    )
    (tmp_path / "usercache.json").write_text(
        json.dumps(
            [
                {
                    "name": "PotatoSalad",
                    "uuid": "db34e03e-7933-3bdf-bafa-22a1431b8881",
                    "expiresOn": "2026-07-02 00:58:28 +0800",
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "whitelist.json").write_text("[]", encoding="utf-8")
    (tmp_path / "world" / "stats" / "001fe3f0-9f9b-3257-a003-3f3a70fdfef9.json").write_text(
        "{}",
        encoding="utf-8",
    )

    players = MinecraftData(tmp_path).list_players()

    assert [(player.username, player.has_stats) for player in players] == [
        ("PotatoSalad", False),
        ("wHo6933", True),
    ]


def test_list_players_deduplicates_username_and_prefers_offline_stats(tmp_path) -> None:
    (tmp_path / "world" / "stats").mkdir(parents=True)
    offline = str(offline_uuid("fullerz"))
    online = "380b48e9-d466-46f9-9f8f-89d02cc28b0e"
    (tmp_path / "usernamecache.json").write_text(
        json.dumps({offline: "fullerz"}),
        encoding="utf-8",
    )
    (tmp_path / "usercache.json").write_text(
        json.dumps(
            [
                {"name": "fullerz", "uuid": offline, "expiresOn": "2026-07-02 11:37:46 +0800"},
                {"name": "fullerz", "uuid": online, "expiresOn": "2026-07-01 23:29:27 +0800"},
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "whitelist.json").write_text(
        json.dumps([{"name": "fullerz", "uuid": online}]),
        encoding="utf-8",
    )
    (tmp_path / "world" / "stats" / f"{offline}.json").write_text("{}", encoding="utf-8")

    players = MinecraftData(tmp_path).list_players()

    assert [(player.username, player.uuid, player.has_stats) for player in players] == [
        ("fullerz", offline, True)
    ]

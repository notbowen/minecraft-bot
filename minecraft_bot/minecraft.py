from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass
from hashlib import md5
from pathlib import Path
from typing import Any


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")


def normalize_username(username: str) -> str:
    username = username.strip()
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("Minecraft usernames must be 3-16 letters, numbers, or underscores")
    return username


def offline_uuid(username: str) -> uuid.UUID:
    digest = bytearray(md5(f"OfflinePlayer:{username}".encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30
    digest[8] = (digest[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(digest))


@dataclass(frozen=True)
class PlayerRecord:
    username: str
    uuid: str
    has_stats: bool


@dataclass(frozen=True)
class WhitelistResult:
    username: str
    uuid: str
    changed: bool
    action: str


@dataclass(frozen=True)
class WhitelistRemovalResult:
    username: str
    uuid: str
    changed: bool
    action: str


class MinecraftData:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.whitelist_path = data_dir / "whitelist.json"
        self.usercache_path = data_dir / "usercache.json"
        self.usernamecache_path = data_dir / "usernamecache.json"
        self.stats_dir = data_dir / "world" / "stats"

    def add_to_whitelist(self, username: str) -> WhitelistResult:
        username = normalize_username(username)
        user_uuid = str(offline_uuid(username))
        whitelist = self._load_json(self.whitelist_path, [])
        if not isinstance(whitelist, list):
            raise ValueError(f"{self.whitelist_path} must contain a JSON list")

        changed = False
        found = False
        for entry in whitelist:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("uuid", "")).casefold() != user_uuid:
                continue
            found = True
            if entry.get("name") != username:
                entry["name"] = username
                changed = True

        if not found:
            whitelist.append({"uuid": user_uuid, "name": username})
            changed = True

        if changed:
            self._write_json(self.whitelist_path, whitelist)

        if found and changed:
            action = "updated"
        elif found:
            action = "already whitelisted"
        else:
            action = "added"
        return WhitelistResult(username=username, uuid=user_uuid, changed=changed, action=action)

    def remove_from_whitelist(self, username: str, user_uuid: str | None = None) -> WhitelistRemovalResult:
        username = normalize_username(username)
        if user_uuid is None:
            user_uuid = str(offline_uuid(username))

        whitelist = self._load_json(self.whitelist_path, [])
        if not isinstance(whitelist, list):
            raise ValueError(f"{self.whitelist_path} must contain a JSON list")

        kept_entries: list[Any] = []
        removed = False
        for entry in whitelist:
            if not isinstance(entry, dict):
                kept_entries.append(entry)
                continue

            entry_uuid = str(entry.get("uuid", ""))
            entry_name = str(entry.get("name", ""))
            if entry_uuid.casefold() == user_uuid.casefold() or entry_name.casefold() == username.casefold():
                removed = True
                continue

            kept_entries.append(entry)

        if removed:
            self._write_json(self.whitelist_path, kept_entries)

        action = "removed" if removed else "not present"
        return WhitelistRemovalResult(username=username, uuid=user_uuid, changed=removed, action=action)

    def list_players(self) -> list[PlayerRecord]:
        names_by_uuid: dict[str, str] = {}

        username_cache = self._load_json(self.usernamecache_path, {})
        if isinstance(username_cache, dict):
            for player_uuid, username in username_cache.items():
                if isinstance(player_uuid, str) and isinstance(username, str) and username:
                    names_by_uuid[player_uuid.casefold()] = username

        user_cache = self._load_json(self.usercache_path, [])
        if isinstance(user_cache, list):
            for entry in user_cache:
                if not isinstance(entry, dict):
                    continue
                player_uuid = str(entry.get("uuid", ""))
                username = str(entry.get("name", ""))
                if player_uuid and username:
                    names_by_uuid.setdefault(player_uuid.casefold(), username)

        whitelist = self._load_json(self.whitelist_path, [])
        if isinstance(whitelist, list):
            for entry in whitelist:
                if not isinstance(entry, dict):
                    continue
                player_uuid = str(entry.get("uuid", ""))
                username = str(entry.get("name", ""))
                if player_uuid and username:
                    names_by_uuid.setdefault(player_uuid.casefold(), username)

        stat_uuids = {
            path.stem.casefold()
            for path in self.stats_dir.glob("*.json")
            if path.is_file()
        } if self.stats_dir.exists() else set()

        records_by_name: dict[str, PlayerRecord] = {}
        for record in [
            PlayerRecord(
                username=username,
                uuid=player_uuid,
                has_stats=player_uuid.casefold() in stat_uuids,
            )
            for player_uuid, username in names_by_uuid.items()
        ]:
            key = record.username.casefold()
            existing = records_by_name.get(key)
            if existing is None or self._player_record_score(record) > self._player_record_score(existing):
                records_by_name[key] = record

        return sorted(records_by_name.values(), key=lambda record: record.username.casefold())

    def find_player(self, username: str) -> PlayerRecord:
        username = normalize_username(username)
        for record in self.list_players():
            if record.username.casefold() == username.casefold():
                return record
        player_uuid = str(offline_uuid(username))
        return PlayerRecord(
            username=username,
            uuid=player_uuid,
            has_stats=(self.stats_dir / f"{player_uuid}.json").exists(),
        )

    def read_stats(self, player_uuid: str) -> dict[str, Any] | None:
        path = self.stats_dir / f"{player_uuid}.json"
        if not path.exists():
            return None
        data = self._load_json(path, {})
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a JSON object")
        return data

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as file:
            text = file.read().strip()
        if not text:
            return default
        return json.loads(text)

    def _player_record_score(self, record: PlayerRecord) -> tuple[bool, bool]:
        return (
            record.has_stats,
            record.uuid.casefold() == str(offline_uuid(record.username)).casefold(),
        )

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = path.stat().st_mode if path.exists() else None
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
                file.write("\n")
            if mode is not None:
                os.chmod(tmp_name, mode)
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

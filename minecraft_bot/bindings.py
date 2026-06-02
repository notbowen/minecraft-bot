from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Binding:
    discord_id: str
    discord_name: str
    username: str
    uuid: str
    bound_at: str


class BindingStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def get(self, discord_id: int | str) -> Binding | None:
        raw = self._load().get("bindings", {}).get(str(discord_id))
        if not isinstance(raw, dict):
            return None
        return Binding(
            discord_id=str(discord_id),
            discord_name=str(raw.get("discord_name", "")),
            username=str(raw.get("username", "")),
            uuid=str(raw.get("uuid", "")),
            bound_at=str(raw.get("bound_at", "")),
        )

    def find_by_username(self, username: str) -> Binding | None:
        target = username.casefold()
        for discord_id, raw in self._load().get("bindings", {}).items():
            if not isinstance(raw, dict):
                continue
            if str(raw.get("username", "")).casefold() == target:
                return Binding(
                    discord_id=str(discord_id),
                    discord_name=str(raw.get("discord_name", "")),
                    username=str(raw.get("username", "")),
                    uuid=str(raw.get("uuid", "")),
                    bound_at=str(raw.get("bound_at", "")),
                )
        return None

    def bind(
        self,
        *,
        discord_id: int | str,
        discord_name: str,
        username: str,
        uuid: str,
    ) -> Binding:
        data = self._load()
        bindings = data.setdefault("bindings", {})
        binding = Binding(
            discord_id=str(discord_id),
            discord_name=discord_name,
            username=username,
            uuid=uuid,
            bound_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        bindings[str(discord_id)] = {
            "discord_name": binding.discord_name,
            "username": binding.username,
            "uuid": binding.uuid,
            "bound_at": binding.bound_at,
        }
        self._write(data)
        return binding

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "bindings": {}}
        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError(f"{self.path} must contain a JSON object")
        data.setdefault("version", 1)
        data.setdefault("bindings", {})
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, sort_keys=True)
                file.write("\n")
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

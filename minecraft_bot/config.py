from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    return int(value)


def _optional_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    discord_token: str
    discord_guild_id: int | None
    role_id: int | None
    minecraft_data_dir: Path
    bindings_path: Path
    rcon_host: str
    rcon_port: int
    rcon_password: str
    rcon_timeout_seconds: float
    join_dm_enabled: bool

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise RuntimeError("DISCORD_TOKEN is required")

        data_dir = Path(os.getenv("MINECRAFT_DATA_DIR", "/minecraft-data")).expanduser()
        default_bindings = Path(os.getenv("BOT_DATA_DIR", "/bot-data")) / "bindings.json"
        bindings_path = Path(os.getenv("BINDINGS_PATH", str(default_bindings))).expanduser()

        return cls(
            discord_token=token,
            discord_guild_id=_optional_int(os.getenv("DISCORD_GUILD_ID")),
            role_id=_optional_int(os.getenv("ROLE_ID")),
            minecraft_data_dir=data_dir,
            bindings_path=bindings_path,
            rcon_host=os.getenv("MC_RCON_HOST", "mc").strip() or "mc",
            rcon_port=int(os.getenv("MC_RCON_PORT", "25575")),
            rcon_password=os.getenv("MC_RCON_PASSWORD", "").strip(),
            rcon_timeout_seconds=float(os.getenv("MC_RCON_TIMEOUT_SECONDS", "5")),
            join_dm_enabled=_optional_bool(os.getenv("DISCORD_JOIN_DM"), default=False),
        )

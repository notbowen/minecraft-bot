Minecraft Discord Bot
=====================

Discord slash-command bot for an offline-mode Minecraft server running in Docker.

Commands:

- `/bind <username>` validates the Minecraft username, computes the offline UUID from `OfflinePlayer:<username>`, removes that Discord user's previous whitelist entry, writes the new entry into `whitelist.json`, applies the whitelist to the running server over RCON, stores the Discord binding, and assigns `ROLE_ID` when configured.
- `/info [username]` shows a compact stats summary. Leaving `username` blank inspects your bound account. The username option autocompletes known players from `usernamecache.json`, `usercache.json`, `whitelist.json`, and `world/stats`.
- `/connect` fetches the current public IP from `https://ip.guide` and prints a copy-pastable Minecraft direct-connect address.

Local Setup
-----------

```sh
uv venv
uv pip install -e . pytest
cp .env.example .env
```

Set `DISCORD_TOKEN` in `.env`. Set `DISCORD_GUILD_ID` if you want commands synced immediately to one server instead of globally. Set `ROLE_ID` to the Discord role ID that should be assigned after `/bind`; the bot needs Manage Roles and its highest role must be above that role.

`/connect` uses `IP_GUIDE_URL=https://ip.guide` and `MINECRAFT_CONNECT_PORT=25565` by default.

Production Deploy
-----------------

The included compose file is configured for `beesnuts`, where Minecraft is running as `minecraft-mc-1` on the `minecraft_default` Docker network and data is mounted at `/home/bowen/services/minecraft/data`.

The bot does not depend on changing the compose `WHITELIST` environment variable at runtime. It writes the UUID entry to the mounted `whitelist.json`, sends `whitelist reload` over RCON, and verifies the running server lists the username, so successful binds apply without restarting Minecraft.

```sh
./deploy.sh
```

The deploy script copies the project to `/home/bowen/minecraft-bot`, creates `.env` if missing, fills `MC_RCON_PASSWORD` from the existing Minecraft RCON config when possible, and builds the Docker image. It starts the bot only when `DISCORD_TOKEN` is set in the remote `.env`.

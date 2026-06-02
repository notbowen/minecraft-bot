from __future__ import annotations

import asyncio
import logging
import re

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from .bindings import BindingStore
from .config import Settings
from .minecraft import MinecraftData, WhitelistRemovalResult, normalize_username, offline_uuid
from .rcon import RconClient, RconError
from .stats import summarize_stats


LOGGER = logging.getLogger(__name__)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class MinecraftManager(commands.Cog):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.minecraft = MinecraftData(settings.minecraft_data_dir)
        self.bindings = BindingStore(settings.bindings_path)
        self.rcon = RconClient(
            host=settings.rcon_host,
            port=settings.rcon_port,
            password=settings.rcon_password,
            timeout_seconds=settings.rcon_timeout_seconds,
        )
        self._write_lock = asyncio.Lock()

    async def username_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        del interaction
        current = current.casefold()
        players = await asyncio.to_thread(self.minecraft.list_players)
        choices = [
            app_commands.Choice(name=record.username, value=record.username)
            for record in players
            if current in record.username.casefold()
        ]
        return choices[:25]

    @app_commands.command(name="bind", description="Bind your Discord account to a Minecraft username.")
    @app_commands.describe(username="Your exact Minecraft username")
    async def bind(self, interaction: discord.Interaction, username: str) -> None:
        await interaction.response.defer(thinking=True)

        try:
            username = normalize_username(username)
        except ValueError as error:
            await interaction.followup.send(str(error))
            return

        discord_name = str(interaction.user)
        discord_id = str(interaction.user.id)
        removed_previous: WhitelistRemovalResult | None = None

        async with self._write_lock:
            previous_binding = await asyncio.to_thread(self.bindings.get, discord_id)
            existing = await asyncio.to_thread(self.bindings.find_by_username, username)
            if existing is not None and existing.discord_id != discord_id:
                await interaction.followup.send(
                    f"`{existing.username}` is already bound to another Discord user.",
                )
                return

            if previous_binding is not None:
                new_uuid = str(offline_uuid(username))
                previous_changed = (
                    previous_binding.uuid.casefold() != new_uuid.casefold()
                    or previous_binding.username != username
                )
                if previous_changed:
                    removed_previous = await asyncio.to_thread(
                        self.minecraft.remove_from_whitelist,
                        previous_binding.username,
                        previous_binding.uuid,
                    )

            result = await asyncio.to_thread(self.minecraft.add_to_whitelist, username)
            await asyncio.to_thread(
                self.bindings.bind,
                discord_id=discord_id,
                discord_name=discord_name,
                username=result.username,
                uuid=result.uuid,
            )

        removed_username = _removed_username_for_verification(result.username, removed_previous)
        whitelist_note = await self._reload_and_verify_whitelist(
            result.username,
            removed_username=removed_username,
        )
        role_note = await self._assign_bind_role(interaction)
        removal_note = _format_removal_note(removed_previous)
        await interaction.followup.send(
            (
                f"Bound you to `{result.username}` (`{result.uuid}`). "
                f"Whitelist entry {result.action}. {removal_note}{whitelist_note} {role_note}"
            ),
        )

    @app_commands.command(name="info", description="Show Minecraft stats for a username.")
    @app_commands.describe(username="Leave blank to inspect your bound username")
    @app_commands.autocomplete(username=username_autocomplete)
    async def info(
        self,
        interaction: discord.Interaction,
        username: str | None = None,
    ) -> None:
        await interaction.response.defer(thinking=True)

        if username is None:
            binding = await asyncio.to_thread(self.bindings.get, interaction.user.id)
            if binding is None:
                await interaction.followup.send(
                    "You are not bound yet. Use `/bind <username>` first.",
                )
                return
            username = binding.username

        try:
            player = await asyncio.to_thread(self.minecraft.find_player, username)
        except ValueError as error:
            await interaction.followup.send(str(error))
            return

        stats_data = await asyncio.to_thread(self.minecraft.read_stats, player.uuid)
        if stats_data is None:
            await interaction.followup.send(
                f"No stats found for `{player.username}` yet.",
            )
            return

        summary = summarize_stats(stats_data)
        embed = discord.Embed(
            title=f"{player.username} Minecraft stats",
            color=discord.Color.green(),
        )
        embed.add_field(name="Overview", value=summary.overview, inline=False)
        embed.add_field(name="Top mined", value=summary.top_mined, inline=True)
        embed.add_field(name="Top crafted", value=summary.top_crafted, inline=True)
        embed.add_field(name="Top killed", value=summary.top_killed, inline=True)
        embed.add_field(name="Top used", value=summary.top_used, inline=True)
        await interaction.followup.send(embed=embed)

    async def _reload_and_verify_whitelist(self, username: str, *, removed_username: str | None = None) -> str:
        try:
            reload_response = await self.rcon.execute("whitelist reload")
            list_response = await self.rcon.execute("whitelist list")
        except (OSError, asyncio.TimeoutError, RconError) as error:
            LOGGER.warning("Whitelist reload failed: %s", error)
            return "I updated the file, but could not reload the running server whitelist; an admin should check RCON."

        new_username_present = _whitelist_list_contains(list_response, username)
        removed_username_absent = (
            removed_username is None
            or not _whitelist_list_contains(list_response, removed_username)
        )
        if new_username_present and removed_username_absent:
            return "Whitelist reloaded and verified on the running server."

        if new_username_present and not removed_username_absent:
            return (
                f"I verified `{username}` on the running whitelist, but `{removed_username}` "
                "is still listed."
            )

        reload_response = reload_response.strip()
        if reload_response:
            return (
                f"Server replied `{reload_response}`, but I could not verify `{username}` "
                "in the running whitelist."
            )
        return f"I reloaded the whitelist, but could not verify `{username}` in the running whitelist."

    async def _assign_bind_role(self, interaction: discord.Interaction) -> str:
        if self.settings.role_id is None:
            return "No Discord role was configured."
        if interaction.guild is None:
            return "I could not assign a Discord role outside a server."
        if not isinstance(interaction.user, discord.Member):
            return "I could not resolve your server membership to assign the Discord role."

        role = interaction.guild.get_role(self.settings.role_id)
        if role is None:
            try:
                role = await interaction.guild.fetch_role(self.settings.role_id)
            except discord.HTTPException as error:
                LOGGER.warning("Could not fetch role %s: %s", self.settings.role_id, error)
                return "I could not find the configured Discord role."

        if role in interaction.user.roles:
            return f"You already have the `{role.name}` role."

        try:
            await interaction.user.add_roles(role, reason="Minecraft account bound")
        except discord.Forbidden:
            return "I could not assign the configured Discord role; check bot role hierarchy and Manage Roles permission."
        except discord.HTTPException as error:
            LOGGER.warning("Could not assign role %s to %s: %s", role.id, interaction.user.id, error)
            return "I could not assign the configured Discord role due to a Discord API error."

        return f"I gave you the `{role.name}` role."


class MinecraftDiscordBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.members = settings.join_dm_enabled
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.settings = settings

    async def setup_hook(self) -> None:
        await self.add_cog(MinecraftManager(self.settings))
        if self.settings.discord_guild_id is not None:
            guild = discord.Object(id=self.settings.discord_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            LOGGER.info("Synced %s guild commands to %s", len(synced), guild.id)
        else:
            synced = await self.tree.sync()
            LOGGER.info("Synced %s global commands", len(synced))

    async def on_ready(self) -> None:
        LOGGER.info("Logged in as %s", self.user)

    async def on_member_join(self, member: discord.Member) -> None:
        if not self.settings.join_dm_enabled:
            return
        try:
            await member.send("Use `/bind <username>` in the server to whitelist your Minecraft account.")
        except discord.HTTPException:
            LOGGER.info("Could not DM new member %s", member.id)


def run() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = Settings.from_env()
    bot = MinecraftDiscordBot(settings)
    bot.run(settings.discord_token)


def _whitelist_list_contains(response: str, username: str) -> bool:
    response = ANSI_RE.sub("", response)
    _, _, names_text = response.partition(":")
    if not names_text:
        return False
    names = [name.strip().casefold() for name in names_text.split(",")]
    return username.casefold() in names


def _removed_username_for_verification(
    username: str,
    removed_previous: WhitelistRemovalResult | None,
) -> str | None:
    if removed_previous is None or not removed_previous.changed:
        return None
    if removed_previous.username.casefold() == username.casefold():
        return None
    return removed_previous.username


def _format_removal_note(removed_previous: WhitelistRemovalResult | None) -> str:
    if removed_previous is None:
        return ""
    if removed_previous.changed:
        return f"Removed your previous whitelist entry `{removed_previous.username}`. "
    return f"Your previous whitelist entry `{removed_previous.username}` was already absent. "

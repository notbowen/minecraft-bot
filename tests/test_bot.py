from __future__ import annotations

from minecraft_bot.bot import (
    _format_removal_note,
    _removed_username_for_verification,
    _whitelist_list_contains,
)
from minecraft_bot.minecraft import WhitelistRemovalResult


def test_whitelist_list_contains_username() -> None:
    response = "There are 6 whitelisted player(s): , , , , fullerz, codexfiletmp\x1b[0m"

    assert _whitelist_list_contains(response, "CodexFileTmp")


def test_whitelist_list_contains_rejects_missing_username() -> None:
    response = "There are 5 whitelisted player(s): , , , , fullerz"

    assert not _whitelist_list_contains(response, "CodexFileTmp")


def test_removed_username_for_verification_skips_same_username() -> None:
    removal = WhitelistRemovalResult(
        username="Steve",
        uuid="old-uuid",
        changed=True,
        action="removed",
    )

    assert _removed_username_for_verification("steve", removal) is None


def test_removed_username_for_verification_returns_different_username() -> None:
    removal = WhitelistRemovalResult(
        username="Steve",
        uuid="old-uuid",
        changed=True,
        action="removed",
    )

    assert _removed_username_for_verification("Alex", removal) == "Steve"


def test_format_removal_note_reports_removed_entry() -> None:
    removal = WhitelistRemovalResult(
        username="Steve",
        uuid="old-uuid",
        changed=True,
        action="removed",
    )

    assert _format_removal_note(removal) == "Removed your previous whitelist entry `Steve`. "

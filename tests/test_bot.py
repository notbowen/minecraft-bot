from __future__ import annotations

from minecraft_bot.bot import (
    _format_removal_note,
    _format_player_count_status,
    _parse_player_count_response,
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


def test_parse_player_count_response() -> None:
    response = "There are 3 of a max of 20 players online: Steve, Alex, fullerz\x1b[0m"

    assert _parse_player_count_response(response) == (3, 20)


def test_parse_player_count_response_rejects_unknown_format() -> None:
    assert _parse_player_count_response("No players are available") is None


def test_format_player_count_status_plural() -> None:
    assert _format_player_count_status(0, 20) == "0/20 players online"


def test_format_player_count_status_singular() -> None:
    assert _format_player_count_status(1, 20) == "1/20 player online"


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

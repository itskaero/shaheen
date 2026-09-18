"""/help's catalog (docs/DECISIONS.md ADR-087).

The catalog in bot/content/help_embeds.py is hand-written so it can group
commands the way a member thinks about them and mark the staff-only ones.
The cost of hand-writing is drift, so the first test here walks the real
command tree and demands an exact match — add a command without listing it
and this fails.
"""

from __future__ import annotations

import importlib
import inspect

from discord import app_commands
from discord.ext import commands

from bot.client import STARTUP_EXTENSIONS
from bot.content.help_embeds import HELP_SECTIONS, build_help_embed

# Discord's own limits — an embed over either of these is rejected at send
# time, which /help must never risk since it is the recovery command.
_MAX_EMBED_TOTAL = 6000
_MAX_FIELD_VALUE = 1024


def _registered_command_names() -> set[str]:
    names: set[str] = set()
    for extension in STARTUP_EXTENSIONS:
        module = importlib.import_module(extension)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                not issubclass(obj, commands.Cog)
                or obj is commands.Cog
                or obj.__module__ != module.__name__
            ):
                continue
            for command in obj.__cog_app_commands__:
                if isinstance(command, app_commands.Group):
                    names.update(f"/{command.name} {sub.name}" for sub in command.commands)
                else:
                    names.add(f"/{command.name}")
    return names


def _catalog_command_names() -> set[str]:
    return {c.name for section in HELP_SECTIONS for c in section.commands}


def test_catalog_lists_exactly_the_registered_commands() -> None:
    registered = _registered_command_names()
    catalogued = _catalog_command_names()
    assert catalogued - registered == set(), "catalog lists commands that do not exist"
    assert registered - catalogued == set(), "commands are missing from /help"


def test_catalog_has_no_duplicates() -> None:
    names = [c.name for section in HELP_SECTIONS for c in section.commands]
    assert len(names) == len(set(names))


def test_section_keys_are_unique() -> None:
    keys = [section.key for section in HELP_SECTIONS]
    assert len(keys) == len(set(keys))


def test_full_embed_fits_discord_limits() -> None:
    embed = build_help_embed()
    assert len(embed.fields) == len(HELP_SECTIONS)
    assert all(len(field.value) <= _MAX_FIELD_VALUE for field in embed.fields)
    total = len(embed.title or "") + len(embed.description or "")
    total += sum(len(f.name or "") + len(f.value or "") for f in embed.fields)
    assert total <= _MAX_EMBED_TOTAL


def test_section_embed_shows_only_that_section() -> None:
    embed = build_help_embed("tournaments")
    assert embed.description is not None
    assert "/tournament register" in embed.description
    assert "/link" not in embed.description


def test_unknown_section_falls_back_to_everything() -> None:
    """/help is what someone runs when they are already lost — it must not
    error on a bad argument.
    """
    embed = build_help_embed("not-a-section")
    assert len(embed.fields) == len(HELP_SECTIONS)


def test_staff_commands_are_marked() -> None:
    staff = [c for section in HELP_SECTIONS for c in section.commands if c.staff_only]
    assert {"/ban", "/kick", "/setup run"} <= {c.name for c in staff}
    embed = build_help_embed("staff")
    assert embed.description is not None and "*(staff)*" in embed.description

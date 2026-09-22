"""/help — the command catalog (docs/DECISIONS.md ADR-087).

Shaheen has 40+ slash commands and, until now, no way to discover them
inside Discord. Discord's own command picker shows names but no grouping and
no sense of which commands are staff-only.

The catalog below is written by hand rather than introspected off the
command tree. Introspection would give names and one-line descriptions for
free, but it can't group commands the way a member thinks about them, can't
say "staff only" (that lives in a decorator), and can't add the short
"why you'd use this" copy that makes a list of 40 names usable.

The cost of hand-writing it is drift, so tests/test_help_embeds.py asserts
the catalog and the real command tree name exactly the same commands — add a
command without listing it here and the suite fails.
"""

from __future__ import annotations

from dataclasses import dataclass

import discord

from bot.palette import EMERALD, GOLD


@dataclass(frozen=True)
class CommandHelp:
    name: str
    summary: str
    staff_only: bool = False


@dataclass(frozen=True)
class HelpSection:
    key: str
    title: str
    commands: tuple[CommandHelp, ...]


HELP_SECTIONS: tuple[HelpSection, ...] = (
    HelpSection(
        key="start",
        title="🦅 Getting Started",
        commands=(
            CommandHelp("/apply", "Apply for the clan roster — approval makes you Trial Shaheen."),
            CommandHelp("/application", "Check the status of your application."),
            CommandHelp("/link", "Link your Brawlhalla account (Steam64 or Brawlhalla ID)."),
            CommandHelp("/unlink", "Remove your active link."),
            CommandHelp("/profile", "Your one-look card: rank, stats, chat level, badges."),
            CommandHelp("/refresh", "Pull your latest stats now instead of waiting for the loop."),
        ),
    ),
    HelpSection(
        key="stats",
        title="📊 Your Stats",
        commands=(
            CommandHelp("/rank", "Current ranked tier, rating, peak and standing."),
            CommandHelp("/stats", "Lifetime level, games and win rate."),
            CommandHelp("/legends", "Per-Legend stats, with ranked rating where you have one."),
            CommandHelp("/history", "Your stored rating history over time."),
            CommandHelp("/achievements", "Which of the 30 clan achievements you hold."),
            CommandHelp("/level", "Your chat level and XP."),
        ),
    ),
    HelpSection(
        key="clan",
        title="🏆 The Clan",
        commands=(
            CommandHelp("/leaderboard", "Shaheen's internal ranked ladder."),
            CommandHelp("/clanstats", "Clan-wide totals, rating spread and tier split."),
            CommandHelp("/legendmeta", "The clan's most-played Legends and their win rates."),
            CommandHelp("/chatboard", "The most active chatters."),
            CommandHelp("/compare", "Two members' stats side by side."),
            CommandHelp("/rivalry", "Head-to-head match record between two members."),
            CommandHelp("/lookup", "Any Brawlhalla player's rank vs the clan — no link needed."),
        ),
    ),
    HelpSection(
        key="play",
        title="⚔️ Playing",
        commands=(
            CommandHelp("/challenge", "Challenge another member to a 1v1."),
            CommandHelp("/scrim", "Announce a scrim for members to join."),
            CommandHelp("/report", "Report a match result for the other side to confirm."),
            CommandHelp("/matches", "A member's match history."),
            CommandHelp("/match create", "Log a match directly between named players."),
            CommandHelp("/match view", "Inspect a match's current status."),
        ),
    ),
    HelpSection(
        key="tournaments",
        title="🥇 Tournaments",
        commands=(
            CommandHelp("/tournament register", "Enter an open tournament."),
            CommandHelp("/tournament bracket", "Show a tournament's current bracket."),
            CommandHelp("/tournament create", "Create a tournament.", staff_only=True),
            CommandHelp("/tournament start", "Lock entries and generate the bracket.", True),
            CommandHelp("/tournament resolve", "Force-resolve a stuck bracket match.", True),
        ),
    ),
    HelpSection(
        key="community",
        title="💬 Community",
        commands=(
            CommandHelp("/suggest", "Anonymously suggest something for the clan."),
            CommandHelp("/help", "This list."),
        ),
    ),
    HelpSection(
        key="staff",
        title="🛡️ Staff — Moderation",
        commands=(
            CommandHelp("/applications", "The queue of applications awaiting review.", True),
            CommandHelp("/verify", "Grant general community access — not roster status.", True),
            CommandHelp("/warn", "Issue a warning.", True),
            CommandHelp("/warnings", "List a member's active warnings.", True),
            CommandHelp("/clearwarnings", "Clear a member's active warnings.", True),
            CommandHelp("/timeout", "Time a member out.", True),
            CommandHelp("/untimeout", "Remove an active timeout.", True),
            CommandHelp("/kick", "Kick a member.", True),
            CommandHelp("/ban", "Ban a member.", True),
            CommandHelp("/unban", "Remove a ban.", True),
            CommandHelp("/nickname", "Set or reset a member's nickname.", True),
            CommandHelp("/purge", "Delete recent messages in a channel.", True),
        ),
    ),
    HelpSection(
        key="staff_server",
        title="🛠️ Staff — Server",
        commands=(
            CommandHelp("/spotlight", "Feature a member in #announcements.", True),
            CommandHelp("/lock", "Stop @everyone from sending in a channel.", True),
            CommandHelp("/unlock", "Undo a /lock on a channel.", True),
            CommandHelp("/slowmode", "Set a channel's slowmode delay.", True),
            CommandHelp("/emoji sync", "Upload Shaheen's legend emoji pack.", True),
            CommandHelp("/emoji browse", "Pick which candidate emoji to upload.", True),
            CommandHelp("/emoji clear", "Delete every custom emoji in the server.", True),
            CommandHelp("/setup run", "Provision the server structure.", True),
            CommandHelp("/setup status", "Show whether expected resources exist.", True),
            CommandHelp("/setup verify", "Non-destructive validation report.", True),
            CommandHelp("/setup reset", "Tear provisioned resources back down.", True),
        ),
    ),
)

SECTION_KEYS: tuple[str, ...] = tuple(section.key for section in HELP_SECTIONS)


def _format(section: HelpSection) -> str:
    return "\n".join(
        f"**{command.name}** — {command.summary}" + (" *(staff)*" if command.staff_only else "")
        for command in section.commands
    )


def build_help_embed(section_key: str | None = None) -> discord.Embed:
    """The whole catalog, or one section when `section_key` matches.

    An unknown key falls back to the full list rather than erroring — /help
    is the command someone runs when they're already lost.
    """
    chosen = next((s for s in HELP_SECTIONS if s.key == section_key), None)

    if chosen is not None:
        embed = discord.Embed(title=f"{chosen.title}", colour=EMERALD)
        embed.description = _format(chosen)
        embed.set_footer(text="/help on its own lists every category.")
        return embed

    embed = discord.Embed(
        title="🦅 Shaheen Commands",
        description=(
            "Everything the bot can do. Most commands reply only to you.\n"
            "Run `/help category:<name>` to see one group on its own."
        ),
        colour=GOLD,
    )
    for section in HELP_SECTIONS:
        embed.add_field(name=section.title, value=_format(section), inline=False)
    embed.set_footer(text="Staff-only commands are marked. New here? Start with /link.")
    return embed

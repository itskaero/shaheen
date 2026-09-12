"""Branded embeds for /link, /unlink, /profile, /rank, /stats, /legends."""

from __future__ import annotations

from datetime import datetime

import discord

from bot.constants import ROLE_TRIAL
from bot.palette import EMERALD, FOREST_GREEN, GOLD, GREY
from database.models.achievement import Achievement
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.chat_activity import ChatActivity
from integrations.brawlhalla.models import PlayerRankedResponse, PlayerStatsResponse
from services.chat_gamification import level_for_xp, rank_title_for_level

_LEGENDS_SHOWN = 10

# GitHub Pages' default project-site URL for this repo (docs/DECISIONS.md
# ADR-047/054) — there's no custom domain configured (no CNAME in web/), and
# no WEBSITE_URL setting exists in core/config.py, so this stays a constant
# here rather than a new required env var just for a footer link. Update
# this (or promote it to a real Settings field) if a custom domain is ever
# set up for the site.
_WEBSITE_BASE_URL = "https://itskaero.github.io/shaheen"


def _legend_display_name(legend_name_key: str) -> str:
    # The API only gives an internal key (e.g. "bodvar"); title-case it as a
    # reasonable display name rather than shipping a full legend name table.
    return legend_name_key.replace("_", " ").title()


def build_link_preview_embed(
    *, candidate_name: str, candidate_id: int, previous_player_name: str | None
) -> discord.Embed:
    description = f"**{candidate_name}** (Brawlhalla ID `{candidate_id}`)"
    if previous_player_name:
        description += f"\n\nThis will replace your current link to **{previous_player_name}**."
    return discord.Embed(title="🦅 Confirm Brawlhalla Link", description=description, colour=GOLD)


def build_link_success_embed(*, player_name: str, promoted: bool) -> discord.Embed:
    description = f"Linked to **{player_name}**."
    if promoted:
        description += f"\n\n🎯 You've been promoted to **{ROLE_TRIAL.name}**. Welcome in!"
    return discord.Embed(title="✅ Brawlhalla Linked", description=description, colour=FOREST_GREEN)


def build_unlink_confirm_embed(player_name: str) -> discord.Embed:
    return discord.Embed(
        title="Confirm Unlink",
        description=f"Remove your link to **{player_name}**?",
        colour=GOLD,
    )


def build_unlink_success_embed(player_name: str) -> discord.Embed:
    return discord.Embed(
        title="✅ Unlinked",
        description=f"Removed your link to **{player_name}**.",
        colour=FOREST_GREEN,
    )


def build_not_linked_embed(target_is_self: bool) -> discord.Embed:
    description = (
        "You haven't linked a Brawlhalla account yet. Use `/link` to get started."
        if target_is_self
        else "That member hasn't linked a Brawlhalla account."
    )
    return discord.Embed(title="No Brawlhalla Link", description=description, colour=GREY)


def build_profile_embed(
    *,
    display_name: str,
    avatar_url: str | None,
    player: BrawlhallaPlayer,
    stats: PlayerStatsResponse,
    ranked: PlayerRankedResponse | None,
    joined_at: datetime | None,
    chat_activity: ChatActivity | None,
    achievements: list[tuple[Achievement, datetime]],
) -> discord.Embed:
    """The one-look profile card — folds in what /rank, /stats, and /legends
    each show separately (win rate, tier/rating/peak, global/region rank)
    plus clan join date, chat-gamification standing, and earned
    achievements (docs/DECISIONS.md ADR-059, extended in ADR-067 — those
    last three already existed elsewhere in the system but never made it
    onto this card). /rank/-stats/-legends stay as-is for a quick
    single-stat check.
    """
    embed = discord.Embed(title=f"🦅 {display_name}", colour=FOREST_GREEN)
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    embed.add_field(
        name="Brawlhalla", value=f"{player.player_name} (Lv. {stats.level})", inline=True
    )
    win_rate = (stats.wins / stats.games * 100) if stats.games else 0.0
    embed.add_field(
        name="Games / Wins", value=f"{stats.games} / {stats.wins} ({win_rate:.0f}%)", inline=True
    )
    if joined_at is not None:
        embed.add_field(name="Member Since", value=joined_at.strftime("%b %d, %Y"), inline=True)

    if ranked is not None and ranked.tier:
        embed.add_field(
            name="Ranked",
            value=f"{ranked.tier} — {ranked.rating} rating (peak {ranked.peak_rating})",
            inline=False,
        )
        if ranked.global_rank:
            embed.add_field(name="Global Rank", value=f"#{ranked.global_rank}", inline=True)
        if ranked.region_rank:
            embed.add_field(name="Region Rank", value=f"#{ranked.region_rank}", inline=True)
        if ranked.region:
            embed.add_field(name="Region", value=ranked.region, inline=True)

    # Derived live from xp, never trusted from ChatActivity's stored
    # `level` column — same rule as bot/cogs/engagement.py's /level and
    # website_service.py's get_community_activity (that column is only
    # updated on a detected level-up, so it can go stale between messages).
    if chat_activity is not None and chat_activity.xp > 0:
        level = level_for_xp(chat_activity.xp)
        embed.add_field(
            name="Chat Rank",
            value=f"{rank_title_for_level(level)} — Level {level} ({chat_activity.xp:,} XP)",
            inline=False,
        )

    if achievements:
        latest_names = ", ".join(a.name for a, _ in achievements[-3:])
        embed.add_field(
            name=f"Achievements ({len(achievements)})", value=latest_names, inline=False
        )

    # Embed footers are plain text (no clickable links) — a field value
    # supports markdown, so the link goes here instead, pointing at what a
    # Discord embed structurally can't show: a rating-history trend chart
    # and full match history (docs/DECISIONS.md ADR-067).
    website_url = f"{_WEBSITE_BASE_URL}/player.html?id={player.brawlhalla_player_id}"
    embed.add_field(
        name="Full Profile", value=f"[Rating trend & match history]({website_url})", inline=False
    )
    return embed


def build_rank_embed(
    *, display_name: str, player: BrawlhallaPlayer, ranked: PlayerRankedResponse | None
) -> discord.Embed:
    embed = discord.Embed(title=f"🏆 {display_name} — Ranked", colour=GOLD)
    if ranked is None or ranked.tier is None:
        embed.description = f"**{player.player_name}** hasn't played ranked yet."
        return embed

    embed.add_field(name="Tier", value=ranked.tier, inline=True)
    embed.add_field(
        name="Rating", value=f"{ranked.rating} (peak {ranked.peak_rating})", inline=True
    )
    embed.add_field(
        name="Record", value=f"{ranked.wins}W — {ranked.games - ranked.wins}L", inline=True
    )
    if ranked.global_rank:
        embed.add_field(name="Global Rank", value=f"#{ranked.global_rank}", inline=True)
    if ranked.region:
        embed.add_field(name="Region", value=ranked.region, inline=True)
    return embed


def build_stats_embed(
    *, display_name: str, player: BrawlhallaPlayer, stats: PlayerStatsResponse
) -> discord.Embed:
    embed = discord.Embed(title=f"📊 {display_name} — Stats", colour=EMERALD)
    embed.add_field(name="Level", value=f"{stats.level}", inline=True)
    embed.add_field(name="Games", value=f"{stats.games}", inline=True)
    win_rate = (stats.wins / stats.games * 100) if stats.games else 0.0
    embed.add_field(name="Wins", value=f"{stats.wins} ({win_rate:.0f}%)", inline=True)
    return embed


def build_legends_embed(
    *, display_name: str, player: BrawlhallaPlayer, stats: PlayerStatsResponse
) -> discord.Embed:
    embed = discord.Embed(title=f"🐺 {display_name} — Legends", colour=FOREST_GREEN)
    if not stats.legends:
        embed.description = f"**{player.player_name}** has no recorded Legend stats yet."
        return embed

    top = sorted(stats.legends, key=lambda legend: legend.games, reverse=True)[:_LEGENDS_SHOWN]
    lines = [
        f"**{_legend_display_name(legend.legend_name_key)}** — {legend.games} games, "
        f"{legend.wins} wins, {legend.kos} KOs, {legend.damagedealt:,} DMG, {legend.falls} falls"
        for legend in top
    ]
    embed.description = "\n".join(lines)
    if len(stats.legends) > _LEGENDS_SHOWN:
        embed.set_footer(
            text=f"Showing top {_LEGENDS_SHOWN} of {len(stats.legends)} Legends played."
        )
    return embed

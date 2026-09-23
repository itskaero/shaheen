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
from services.achievements import CATALOG
from services.chat_gamification import level_for_xp, rank_title_for_level
from services.legend_art import legend_display_name
from services.playstyle import derive_playstyle_tags

_LEGENDS_SHOWN = 10

# GitHub Pages' default project-site URL for this repo (docs/DECISIONS.md
# ADR-047/054) — there's no custom domain configured (no CNAME in web/), and
# no WEBSITE_URL setting exists in core/config.py, so this stays a constant
# here rather than a new required env var just for a footer link. Update
# this (or promote it to a real Settings field) if a custom domain is ever
# set up for the site.
_WEBSITE_BASE_URL = "https://itskaero.github.io/shaheen"


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
    clan_role: str | None = None,
    discord_created_at: datetime | None = None,
    discord_joined_at: datetime | None = None,
) -> discord.Embed:
    """The one-look profile card — folds in what /rank, /stats, and /legends
    each show separately (win rate, tier/rating/peak, global/region rank)
    plus clan join date, chat-gamification standing, and earned
    achievements (docs/DECISIONS.md ADR-059, extended in ADR-067 — those
    last three already existed elsewhere in the system but never made it
    onto this card). Favourite Legend, a derived playstyle, an
    earned/total achievement count, clan role, and Discord account/guild
    dates were added in ADR-096 — the last two exist only here, since
    nothing in the database persists per-member Discord timestamps
    (docs/DECISIONS.md ADR-040). /rank/-stats/-legends stay as-is for a
    quick single-stat check.
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

    if stats.legends:
        favourite = max(stats.legends, key=lambda legend: legend.games)
        embed.add_field(
            name="Favourite Legend",
            value=f"{legend_display_name(favourite.legend_name_key)} ({favourite.games} games)",
            inline=True,
        )
        # A derived label, not a Brawlhalla-reported stat — the API has no
        # such field (docs/DECISIONS.md ADR-096).
        embed.add_field(
            name="Playstyle", value=", ".join(derive_playstyle_tags(stats.legends)), inline=True
        )

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

    if clan_role:
        embed.add_field(name="Clan Role", value=clan_role, inline=True)

    if discord_created_at is not None or discord_joined_at is not None:
        parts = []
        if discord_created_at is not None:
            parts.append(f"Account: {discord_created_at.strftime('%b %Y')}")
        if discord_joined_at is not None:
            parts.append(f"This server: {discord_joined_at.strftime('%b %Y')}")
        embed.add_field(name="Discord", value=" · ".join(parts), inline=True)

    if achievements:
        latest_names = ", ".join(a.name for a, _ in achievements[-3:])
        embed.add_field(
            name=f"Achievements ({len(achievements)}/{len(CATALOG)})",
            value=latest_names,
            inline=False,
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
    *,
    display_name: str,
    player: BrawlhallaPlayer,
    stats: PlayerStatsResponse,
    ranked: PlayerRankedResponse | None = None,
) -> discord.Embed:
    """Lifetime per-Legend stats, annotated with ranked standing where the
    member has played that Legend in ranked.

    The ranked-per-Legend breakdown has been fetched on every snapshot since
    Phase 2 and thrown away unread; this is the first thing that shows it
    (docs/DECISIONS.md ADR-084).
    """
    embed = discord.Embed(title=f"🐺 {display_name} — Legends", colour=FOREST_GREEN)
    if not stats.legends:
        embed.description = f"**{player.player_name}** has no recorded Legend stats yet."
        return embed

    ranked_by_legend = {
        legend.legend_name_key: legend for legend in (ranked.legends if ranked else [])
    }

    top = sorted(stats.legends, key=lambda legend: legend.games, reverse=True)[:_LEGENDS_SHOWN]
    lines = []
    for legend in top:
        line = (
            f"**{legend_display_name(legend.legend_name_key)}** — {legend.games} games, "
            f"{legend.wins} wins, {legend.kos} KOs, {legend.damagedealt:,} DMG, "
            f"{legend.falls} falls"
        )
        ranked_legend = ranked_by_legend.get(legend.legend_name_key)
        if ranked_legend is not None and ranked_legend.rating is not None:
            line += f"\n╰ Ranked: {ranked_legend.rating}"
            if ranked_legend.tier:
                line += f" ({ranked_legend.tier})"
            line += f" · {ranked_legend.wins}W-{ranked_legend.games - ranked_legend.wins}L"
        lines.append(line)
    embed.description = "\n".join(lines)
    if len(stats.legends) > _LEGENDS_SHOWN:
        embed.set_footer(
            text=f"Showing top {_LEGENDS_SHOWN} of {len(stats.legends)} Legends played."
        )
    return embed


def build_compare_embed(
    *,
    left_name: str,
    left_stats: PlayerStatsResponse,
    left_ranked: PlayerRankedResponse | None,
    right_name: str,
    right_stats: PlayerStatsResponse,
    right_ranked: PlayerRankedResponse | None,
) -> discord.Embed:
    """Side-by-side stats for two linked members.

    /rivalry already covers the head-to-head *match* record between two
    members; this is the stats comparison, which nothing covered before
    (docs/DECISIONS.md ADR-084). Rendered as aligned rows rather than two
    columns of embed fields so the numbers actually line up on mobile.
    """
    embed = discord.Embed(title=f"⚔️ {left_name} vs {right_name}", colour=GOLD)

    def row(label: str, left: str, right: str) -> str:
        return f"**{label}**\n{left}  ·  {right}"

    def win_rate(stats: PlayerStatsResponse) -> str:
        rate = (stats.wins / stats.games * 100) if stats.games else 0.0
        return f"{stats.wins:,} ({rate:.0f}%)"

    lines = [
        row("Level", str(left_stats.level), str(right_stats.level)),
        row("Career Games", f"{left_stats.games:,}", f"{right_stats.games:,}"),
        row("Career Wins", win_rate(left_stats), win_rate(right_stats)),
    ]

    def ranked_value(ranked: PlayerRankedResponse | None, attribute: str) -> str:
        if ranked is None or ranked.tier is None:
            return "—"
        value = getattr(ranked, attribute)
        return str(value) if value is not None else "—"

    lines.extend(
        [
            row(
                "Tier",
                ranked_value(left_ranked, "tier"),
                ranked_value(right_ranked, "tier"),
            ),
            row(
                "Rating",
                ranked_value(left_ranked, "rating"),
                ranked_value(right_ranked, "rating"),
            ),
            row(
                "Peak Rating",
                ranked_value(left_ranked, "peak_rating"),
                ranked_value(right_ranked, "peak_rating"),
            ),
        ]
    )

    embed.description = "\n\n".join(lines)

    if (
        left_ranked is not None
        and right_ranked is not None
        and left_ranked.rating is not None
        and right_ranked.rating is not None
    ):
        gap = abs(left_ranked.rating - right_ranked.rating)
        ahead = left_name if left_ranked.rating >= right_ranked.rating else right_name
        embed.set_footer(
            text=(f"{ahead} leads by {gap} rating." if gap else "Dead level on rating.")
        )
    return embed


def build_refresh_embed(
    *,
    display_name: str,
    player: BrawlhallaPlayer,
    ranked: PlayerRankedResponse | None,
    new_achievements: list[str],
) -> discord.Embed:
    embed = build_rank_embed(display_name=display_name, player=player, ranked=ranked)
    embed.title = f"🔄 {display_name} — Refreshed"
    if new_achievements:
        embed.add_field(name="New Achievements", value=", ".join(new_achievements), inline=False)
    return embed


def build_refresh_cooldown_embed(retry_after_seconds: int) -> discord.Embed:
    minutes = max(1, round(retry_after_seconds / 60))
    return discord.Embed(
        title="Already up to date",
        description=(
            f"Your stats were refreshed recently. Try again in about {minutes} minute(s).\n"
            "Snapshots also run automatically on a schedule."
        ),
        colour=GREY,
    )

"""Branded embeds for /lookup (docs/DECISIONS.md ADR-083)."""

from __future__ import annotations

import discord

from bot.palette import GOLD, GREY
from services.clan_service import ClanRankContext
from services.lookup_service import LookupResult

# Shown when resolution fails. Brawlhalla's API has no name search, so the
# copy has to say plainly what's accepted and where to find it — "player not
# found" on its own reads like the player doesn't exist.
IDENTIFIER_HELP = (
    "`/lookup` needs a **Steam64 ID** (17 digits) or a **Brawlhalla ID**.\n"
    "Brawlhalla has no username search, so a name won't work.\n\n"
    "• **Steam64 ID** — open the Steam profile and copy the number from the URL, "
    "or paste the profile link into a Steam ID lookup site.\n"
    "• **Brawlhalla ID** — shown on [the Brawlhalla leaderboards]"
    "(https://www.brawlhalla.com/rankings/) profile URL for that player."
)


def build_lookup_help_embed(reason: str) -> discord.Embed:
    return discord.Embed(
        title="Couldn't look that up",
        description=f"{reason}\n\n{IDENTIFIER_HELP}",
        colour=GREY,
    )


def _clan_context_lines(context: ClanRankContext, rating: int) -> list[str]:
    if context.total_ranked == 0:
        return ["No Shaheen member has a ranked snapshot yet — nothing to compare against."]

    lines = [f"Would place **#{context.would_be_rank}** of {context.total_ranked + 1} in Shaheen."]
    if context.above is not None:
        name, above_rating = context.above
        lines.append(f"⬆️ **{name}** — {above_rating} (+{above_rating - rating})")
    else:
        lines.append("⬆️ Nobody in the clan is rated higher.")
    if context.below is not None:
        name, below_rating = context.below
        lines.append(f"⬇️ **{name}** — {below_rating} (−{rating - below_rating})")
    else:
        lines.append("⬇️ Nobody in the clan is rated lower.")
    return lines


def build_lookup_embed(result: LookupResult) -> discord.Embed:
    """Public Brawlhalla data for an unlinked player, placed against the clan.

    A bare rating means little on its own, so the clan comparison is the
    body of the card rather than a footnote.
    """
    embed = discord.Embed(
        title=f"🔎 {result.player_name}",
        description=f"Brawlhalla ID `{result.brawlhalla_id}` · not linked to a Shaheen member",
        colour=GOLD,
    )

    stats = result.stats
    win_rate = (stats.wins / stats.games * 100) if stats.games else 0.0
    embed.add_field(name="Level", value=f"{stats.level}", inline=True)
    embed.add_field(name="Career Games", value=f"{stats.games:,}", inline=True)
    embed.add_field(name="Career Wins", value=f"{stats.wins:,} ({win_rate:.0f}%)", inline=True)

    ranked = result.ranked
    if ranked is None or ranked.tier is None:
        embed.add_field(name="Ranked", value="No ranked games played this season.", inline=False)
        return embed

    embed.add_field(name="Tier", value=ranked.tier, inline=True)
    embed.add_field(
        name="Rating", value=f"{ranked.rating} (peak {ranked.peak_rating})", inline=True
    )
    embed.add_field(
        name="Ranked Record", value=f"{ranked.wins}W — {ranked.games - ranked.wins}L", inline=True
    )
    if ranked.global_rank:
        embed.add_field(name="Global Rank", value=f"#{ranked.global_rank}", inline=True)
    if ranked.region_rank:
        embed.add_field(name="Region Rank", value=f"#{ranked.region_rank}", inline=True)
    if ranked.region:
        embed.add_field(name="Region", value=ranked.region, inline=True)

    if result.clan_context is not None and ranked.rating is not None:
        embed.add_field(
            name="Against Shaheen",
            value="\n".join(_clan_context_lines(result.clan_context, ranked.rating)),
            inline=False,
        )

    embed.set_footer(text="Public Brawlhalla data — nothing was saved and no account was linked.")
    return embed

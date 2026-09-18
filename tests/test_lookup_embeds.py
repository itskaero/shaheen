"""build_lookup_embed / build_lookup_help_embed (ADR-083).

Pure embed construction — the clan-context block is the reason /lookup
exists, so most of this is about that block reading correctly at the edges
of the ladder.
"""

from __future__ import annotations

from bot.content.lookup_embeds import build_lookup_embed, build_lookup_help_embed
from integrations.brawlhalla.models import PlayerRankedResponse, PlayerStatsResponse
from services.clan_service import ClanRankContext
from services.lookup_service import LookupResult

STATS = PlayerStatsResponse(brawlhalla_id=777, name="Stranger", level=40, games=400, wins=220)


def _field(embed, name: str) -> str | None:
    for field in embed.fields:
        if field.name == name:
            return field.value
    return None


def _result(*, rating: int | None = 1600, context: ClanRankContext | None = None) -> LookupResult:
    ranked = (
        None
        if rating is None
        else PlayerRankedResponse(
            brawlhalla_id=777,
            name="Stranger",
            tier="Diamond",
            rating=rating,
            peak_rating=rating + 40,
            wins=120,
            games=200,
        )
    )
    return LookupResult(
        player_name="Stranger",
        brawlhalla_id=777,
        stats=STATS,
        ranked=ranked,
        clan_context=context,
    )


def test_lookup_embed_shows_the_nearest_clan_members_either_side() -> None:
    embed = build_lookup_embed(
        _result(
            context=ClanRankContext(
                would_be_rank=2, total_ranked=2, above=("Kaero", 1800), below=("Ali", 1400)
            )
        )
    )

    against = _field(embed, "Against Shaheen")
    assert against is not None
    assert "**#2** of 3" in against  # the looked-up player joins the ladder
    assert "Kaero" in against and "+200" in against
    assert "Ali" in against and "200" in against


def test_lookup_embed_at_the_top_of_the_ladder() -> None:
    embed = build_lookup_embed(
        _result(
            rating=2100,
            context=ClanRankContext(
                would_be_rank=1, total_ranked=1, above=None, below=("Kaero", 1800)
            ),
        )
    )

    against = _field(embed, "Against Shaheen")
    assert against is not None
    assert "Nobody in the clan is rated higher." in against


def test_lookup_embed_with_no_ranked_clan_members_says_so() -> None:
    embed = build_lookup_embed(
        _result(context=ClanRankContext(would_be_rank=1, total_ranked=0, above=None, below=None))
    )

    against = _field(embed, "Against Shaheen")
    assert against is not None
    assert "No Shaheen member has a ranked snapshot yet" in against


def test_lookup_embed_for_an_unranked_player_skips_the_comparison() -> None:
    embed = build_lookup_embed(_result(rating=None))

    assert _field(embed, "Ranked") == "No ranked games played this season."
    assert _field(embed, "Against Shaheen") is None


def test_lookup_embed_says_nothing_was_saved() -> None:
    """/lookup is a read-only probe — the card has to make that plain."""
    embed = build_lookup_embed(_result(context=None))
    assert embed.footer.text is not None
    assert "nothing was saved" in embed.footer.text
    assert "not linked" in (embed.description or "")


def test_help_embed_explains_which_identifiers_work() -> None:
    """Brawlhalla has no username search, so "not found" alone is misleading."""
    embed = build_lookup_help_embed("No Brawlhalla player found for 'kaero'.")

    assert embed.description is not None
    assert "Steam64 ID" in embed.description
    assert "no username search" in embed.description
    assert "kaero" in embed.description

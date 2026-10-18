"""The war room (docs/DECISIONS.md ADR-136): when lead changes, the countdown
and the verdict post, the scoreboard and verdict embeds, the MVP award and
the result card."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot.content.war_room_embeds import (
    build_countdown_embed,
    build_lead_change_text,
    build_scoreboard_embed,
    build_verdict_embed,
)
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.guild_settings_repository import GuildSettingsRepository
from services.cities import CityStanding
from services.clan_war_service import ClanWarService
from services.image_service import CLAN_WAR_CARD_SIZE, render_clan_war_card
from services.war_room import COUNTDOWN_WINDOW, WarRoomState, leader, plan
from services.war_room_service import WarRoomService
from tests.test_clan_wars import GUILD, NOW, WEEK_START, _member, _team
from tests.test_staff_service import _link

MON = date(2026, 10, 12)
LAST_MON = date(2026, 10, 5)
ENDS = datetime(2026, 10, 18, 19, tzinfo=UTC)


def _plan(
    state: WarRoomState,
    standings: list[tuple[int, int]],
    *,
    now: datetime = NOW,
    recorded: bool = False,
):  # type: ignore[no-untyped-def]
    return plan(
        state=state,
        now=now,
        week_start=MON,
        ends_at=ENDS,
        standings=standings,
        finished_week=LAST_MON,
        finished_recorded=recorded,
    )


def test_leader_needs_points_and_a_clear_lead() -> None:
    assert leader([]) is None
    assert leader([(1, 0), (2, 0)]) is None
    assert leader([(1, 50), (2, 50)]) is None
    assert leader([(1, 51), (2, 50)]) == 1


def test_a_new_week_sets_the_leader_without_a_lead_change_post() -> None:
    first = _plan(WarRoomState(leader_team_id=9, leader_week=LAST_MON), [(1, 40), (2, 10)])
    assert first.lead_change is None
    assert (first.state.leader_team_id, first.state.leader_week) == (1, MON)

    same = _plan(first.state, [(1, 60), (2, 20)])
    assert same.lead_change is None

    flipped = _plan(same.state, [(2, 70), (1, 60)])
    assert flipped.lead_change == (1, 2)
    assert flipped.state.leader_team_id == 2
    # A tie keeps the last leader without a post.
    tied = _plan(flipped.state, [(2, 70), (1, 70)])
    assert tied.lead_change is None and tied.state.leader_team_id == 2


def test_countdown_posts_once_in_the_last_hours_and_verdict_once() -> None:
    state = WarRoomState(leader_team_id=1, leader_week=MON)
    early = _plan(state, [(1, 10)], now=ENDS - COUNTDOWN_WINDOW - timedelta(minutes=1))
    assert not early.countdown
    late = _plan(state, [(1, 10)], now=ENDS - timedelta(hours=2))
    assert late.countdown and late.state.countdown_week == MON
    assert not _plan(late.state, [(1, 10)], now=ENDS - timedelta(hours=1)).countdown
    # Nobody has scored: no countdown.
    assert not _plan(WarRoomState(), [(1, 0)], now=ENDS - timedelta(hours=1)).countdown

    verdict = _plan(state, [(1, 10)], recorded=True)
    assert verdict.verdict and verdict.state.verdict_week == LAST_MON
    assert not _plan(verdict.state, [(1, 10)], recorded=True).verdict
    assert not _plan(state, [(1, 10)], recorded=False).verdict


async def test_view_records_last_week_and_awards_a_linked_mvp(session: AsyncSession) -> None:
    red = await _team(session, "Red Hawks", "RH")
    blue = await _team(session, "Blue Wolves", "BW")
    last_start = WEEK_START - timedelta(days=7)
    before_last = last_start - timedelta(hours=1)
    end_last = WEEK_START - timedelta(hours=1)
    await _member(session, red, 1, [(before_last, 20, 1500), (end_last, 26, 1550)])
    await _member(session, blue, 2, [(before_last, 20, 1500), (end_last, 21, 1500)])
    await _link(session, 555, 1, "P1")  # the MVP is linked to Discord 555
    await GuildSettingsRepository(session).set_war_room(GUILD, channel_id=42)

    service = WarRoomService(session, min_games=10)
    view = await service.view(GUILD, now=NOW)
    assert view.finished is not None and view.plan.verdict
    assert view.finished.mvp is not None and view.finished.mvp.player.player_name == "P1"
    assert await service.award_mvp(GUILD, view.finished.mvp.player.id) == 555
    blue_player = await BrawlhallaPlayerRepository(session).get_by_brawlhalla_id(2)
    assert blue_player is not None
    assert await service.award_mvp(GUILD, blue_player.id) is None  # not linked

    await service.save_state(GUILD, view.plan.state)
    again = await service.view(GUILD, now=NOW + timedelta(minutes=15))
    assert not again.plan.verdict
    config = await service.config(GUILD)
    assert config.channel_id == 42 and config.state.verdict_week == LAST_MON


async def test_embeds_and_card_render(session: AsyncSession) -> None:
    red = await _team(session, "Red Hawks", "RH")
    blue = await _team(session, "Blue Wolves", "BW")
    before = WEEK_START - timedelta(hours=3)
    await _member(session, red, 1, [(before, 20, 1500), (NOW - timedelta(hours=1), 24, 1540)])
    await _member(session, blue, 2, [(before, 20, 1500), (NOW - timedelta(hours=1), 21, 1500)])
    week = await ClanWarService(session).week(GUILD, now=NOW)

    board = build_scoreboard_embed(
        week=week,
        cities=[CityStanding("lahore", "Lahore", 1700, 3)],
        site_url="https://example.test",
        now=NOW,
    )
    text = str(board.to_dict())
    assert "Red Hawks" in text and "Lahore" in text and "duels" in text
    assert "took the lead" in build_lead_change_text(
        week=week, old_leader=blue.id, new_leader=red.id
    )
    assert build_countdown_embed(week=week, site_url="https://example.test").title
    verdict = build_verdict_embed(week=week, site_url="https://example.test", mvp_mention="<@5>")
    assert verdict.title == "🏆 Red Hawks win the week!"
    assert "<@5>" in str(verdict.to_dict())

    png = render_clan_war_card(
        week_label="week of 12 Oct",
        standings=[
            ("A Very Long Clan Name That Keeps Going", "LONG", 1234, "#123456"),
            ("B", "B", 1, None),
        ],
        mvp=("Somebody", 99, None),
        site="example.test/clanwars.html",
    )
    from io import BytesIO

    from PIL import Image

    assert png.startswith(b"\x89PNG") and Image.open(BytesIO(png)).size == CLAN_WAR_CARD_SIZE

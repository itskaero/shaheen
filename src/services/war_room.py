"""The war room's rules (docs/DECISIONS.md ADR-136). Pure: no database, no Discord.

The bot keeps a live scoreboard in the war-room channel and, around it, posts
three kinds of moment, each at most once:
- a lead change: a different team takes first place in the live week;
- the countdown: once, in the last COUNTDOWN_WINDOW of the week;
- the verdict: once, after a finished week has been recorded.
The state remembers what has been posted, so a restart never posts twice.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

COUNTDOWN_WINDOW = timedelta(hours=6)


@dataclass(frozen=True)
class WarRoomState:
    leader_team_id: int | None = None
    leader_week: date | None = None
    countdown_week: date | None = None
    verdict_week: date | None = None


@dataclass(frozen=True)
class WarRoomPlan:
    state: WarRoomState
    # (previous leader, new leader) when the lead changed hands.
    lead_change: tuple[int, int] | None = None
    countdown: bool = False
    verdict: bool = False


def leader(standings: Sequence[tuple[int, int]]) -> int | None:
    """The team strictly ahead, from (team_id, points) best first. None when
    nobody has scored or the top is tied."""
    if not standings or standings[0][1] <= 0:
        return None
    if len(standings) > 1 and standings[1][1] == standings[0][1]:
        return None
    return standings[0][0]


def plan(
    *,
    state: WarRoomState,
    now: datetime,
    week_start: date,
    ends_at: datetime,
    standings: Sequence[tuple[int, int]],
    finished_week: date,
    finished_recorded: bool,
) -> WarRoomPlan:
    """What to post now. `standings` is the live week's (team_id, points);
    `finished_recorded` says last week's result is stored."""
    new = state
    lead_change: tuple[int, int] | None = None
    current = leader(standings)

    if state.leader_week != week_start:
        # A new week: remember who leads without calling it a lead change.
        new = replace(new, leader_team_id=current, leader_week=week_start)
    elif current is not None and current != state.leader_team_id:
        if state.leader_team_id is not None:
            lead_change = (state.leader_team_id, current)
        new = replace(new, leader_team_id=current)

    countdown = (
        ends_at - COUNTDOWN_WINDOW <= now < ends_at
        and state.countdown_week != week_start
        and current is not None
    )
    if countdown:
        new = replace(new, countdown_week=week_start)

    verdict = finished_recorded and state.verdict_week != finished_week
    if verdict:
        new = replace(new, verdict_week=finished_week)

    return WarRoomPlan(state=new, lead_change=lead_change, countdown=countdown, verdict=verdict)

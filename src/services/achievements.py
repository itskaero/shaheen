"""Achievement catalog and pure evaluation logic (docs/DECISIONS.md ADR-030, ADR-081).

No Discord or database dependency here — every evaluate_* function takes
plain values and returns which achievements were newly earned, the same
"pure planning, testable in isolation" shape as services/setup_planner.py.
Persisting and announcing them is services/achievement_service.py's job.

This module is the source of truth for the catalog; migrations seed the
`achievements` table from a literal copy of these values rather than
importing this module, since migrations should stay stable even if this
catalog changes later.

ADR-081 grew the catalog from 5 to 30 and added three evaluation sources
beyond ranked snapshots. The old catalog couldn't tell members apart:
first_link is awarded to everyone who links, and games_100/games_500
measure *lifetime career games*, which an established player clears on
their very first snapshot — so only the two tier achievements ever varied.
Competition, community and tenure awarded nothing at all.
"""

from __future__ import annotations

from dataclasses import dataclass

# Ordered lowest to highest. Best-effort and may not match every real tier
# name the API returns — see docs/DECISIONS.md ADR-031: an unrecognized
# tier simply doesn't match, it never raises.
_TIER_ORDER = ("tin", "bronze", "silver", "gold", "platinum", "diamond", "diamond+", "valhallan")

# A ranked win rate is only meaningful over a real sample — without this
# floor a single lucky win would read as a 100% win rate.
MIN_RANKED_GAMES_FOR_WIN_RATE = 50


@dataclass(frozen=True)
class AchievementDef:
    key: str
    name: str
    description: str
    # Groups the gallery and the per-member checklist on the website so a
    # 30-entry catalog stays readable (ADR-081).
    category: str


# --- onboarding -----------------------------------------------------------

FIRST_LINK = AchievementDef(
    "first_link", "First Contact", "Linked a Brawlhalla account to Shaheen.", "onboarding"
)

# --- lifetime games -------------------------------------------------------

GAMES_100 = AchievementDef("games_100", "Centurion", "Played 100 games.", "milestone")
GAMES_500 = AchievementDef("games_500", "Battle-Hardened", "Played 500 games.", "milestone")
GAMES_1000 = AchievementDef(
    "games_1000", "Veteran of a Thousand", "Played 1,000 games.", "milestone"
)
GAMES_2500 = AchievementDef("games_2500", "Relentless", "Played 2,500 games.", "milestone")
GAMES_5000 = AchievementDef("games_5000", "Unbroken", "Played 5,000 games.", "milestone")

# --- ranked tier ----------------------------------------------------------

TIER_GOLD = AchievementDef("tier_gold", "Gold Shaheen", "Reached Gold tier in ranked.", "ranked")
TIER_PLATINUM = AchievementDef(
    "tier_platinum", "Platinum Shaheen", "Reached Platinum tier in ranked.", "ranked"
)
TIER_DIAMOND_PLUS = AchievementDef(
    "tier_diamond_plus", "Diamond Shaheen", "Reached Diamond tier or higher in ranked.", "ranked"
)
TIER_VALHALLAN = AchievementDef(
    "tier_valhallan", "Valhallan", "Reached Valhallan — the top of the ladder.", "ranked"
)

# --- peak rating ----------------------------------------------------------

PEAK_1500 = AchievementDef("peak_1500", "Ascendant", "Hit a peak rating of 1500.", "ranked")
PEAK_1800 = AchievementDef("peak_1800", "Skyborne", "Hit a peak rating of 1800.", "ranked")
PEAK_2000 = AchievementDef("peak_2000", "Above the Clouds", "Hit a peak rating of 2000.", "ranked")

# --- standings ------------------------------------------------------------

GLOBAL_TOP_1000 = AchievementDef(
    "global_top_1000", "Global Elite", "Ranked inside the global top 1,000.", "ranked"
)
# "Region" is the Brawlhalla server region's 1v1 ladder (SEA, EU, US-E...) —
# the API's region_rank — not a country (docs/DECISIONS.md ADR-100).
REGION_TOP_100 = AchievementDef(
    "region_top_100",
    "Regional Force",
    "Ranked inside the top 100 of your Brawlhalla server region's 1v1 ladder (e.g. SEA).",
    "ranked",
)
WIN_RATE_60 = AchievementDef(
    "win_rate_60",
    "Sharpened",
    f"Held a 60% ranked win rate over {MIN_RANKED_GAMES_FOR_WIN_RATE}+ ranked games.",
    "ranked",
)

# --- clan competition -----------------------------------------------------

FIRST_WIN = AchievementDef("first_win", "First Blood", "Won your first clan match.", "competition")
WINS_10 = AchievementDef("wins_10", "Contender", "Won 10 clan matches.", "competition")
WINS_50 = AchievementDef("wins_50", "Dominator", "Won 50 clan matches.", "competition")
TOURNAMENT_ENTRANT = AchievementDef(
    "tournament_entrant", "Bracket Debut", "Entered your first clan tournament.", "competition"
)
TOURNAMENT_FINALIST = AchievementDef(
    "tournament_finalist", "Finalist", "Reached a clan tournament final.", "competition"
)
TOURNAMENT_CHAMPION = AchievementDef(
    "tournament_champion", "Champion", "Won a clan tournament.", "competition"
)
SCRIM_REGULAR = AchievementDef(
    "scrim_regular", "Sparring Partner", "Joined 10 clan scrims.", "competition"
)

# --- community ------------------------------------------------------------

CHAT_LEVEL_10 = AchievementDef(
    "chat_level_10", "Voice of the Nest", "Reached chat level 10.", "community"
)
CHAT_LEVEL_25 = AchievementDef("chat_level_25", "Nest Elder", "Reached chat level 25.", "community")
CHAT_LEVEL_50 = AchievementDef(
    "chat_level_50", "Keeper of the Nest", "Reached chat level 50.", "community"
)
MVP_OF_WEEK = AchievementDef(
    "mvp_of_week", "MVP of the Week", "Named MVP in a weekly digest.", "community"
)

# --- tenure ---------------------------------------------------------------

VETERAN_30D = AchievementDef("veteran_30d", "One Moon", "30 days with Shaheen.", "tenure")
VETERAN_180D = AchievementDef(
    "veteran_180d", "Half a Year Higher", "180 days with Shaheen.", "tenure"
)
VETERAN_365D = AchievementDef(
    "veteran_365d", "Year of the Shaheen", "365 days with Shaheen.", "tenure"
)


CATALOG: tuple[AchievementDef, ...] = (
    FIRST_LINK,
    GAMES_100,
    GAMES_500,
    GAMES_1000,
    GAMES_2500,
    GAMES_5000,
    TIER_GOLD,
    TIER_PLATINUM,
    TIER_DIAMOND_PLUS,
    TIER_VALHALLAN,
    PEAK_1500,
    PEAK_1800,
    PEAK_2000,
    GLOBAL_TOP_1000,
    REGION_TOP_100,
    WIN_RATE_60,
    FIRST_WIN,
    WINS_10,
    WINS_50,
    TOURNAMENT_ENTRANT,
    TOURNAMENT_FINALIST,
    TOURNAMENT_CHAMPION,
    SCRIM_REGULAR,
    CHAT_LEVEL_10,
    CHAT_LEVEL_25,
    CHAT_LEVEL_50,
    MVP_OF_WEEK,
    VETERAN_30D,
    VETERAN_180D,
    VETERAN_365D,
)

# Threshold tables, lowest first. Keeping these as data rather than a wall
# of if-statements is what lets the evaluators below stay four short loops.
_GAMES_THRESHOLDS: tuple[tuple[int, AchievementDef], ...] = (
    (100, GAMES_100),
    (500, GAMES_500),
    (1000, GAMES_1000),
    (2500, GAMES_2500),
    (5000, GAMES_5000),
)
_TIER_THRESHOLDS: tuple[tuple[str, AchievementDef], ...] = (
    ("gold", TIER_GOLD),
    ("platinum", TIER_PLATINUM),
    ("diamond", TIER_DIAMOND_PLUS),
    ("valhallan", TIER_VALHALLAN),
)
_PEAK_THRESHOLDS: tuple[tuple[int, AchievementDef], ...] = (
    (1500, PEAK_1500),
    (1800, PEAK_1800),
    (2000, PEAK_2000),
)
_MATCH_WIN_THRESHOLDS: tuple[tuple[int, AchievementDef], ...] = (
    (1, FIRST_WIN),
    (10, WINS_10),
    (50, WINS_50),
)
_CHAT_LEVEL_THRESHOLDS: tuple[tuple[int, AchievementDef], ...] = (
    (10, CHAT_LEVEL_10),
    (25, CHAT_LEVEL_25),
    (50, CHAT_LEVEL_50),
)
_TENURE_THRESHOLDS: tuple[tuple[int, AchievementDef], ...] = (
    (30, VETERAN_30D),
    (180, VETERAN_180D),
    (365, VETERAN_365D),
)

# Achievements evaluated from a scheduled snapshot cycle. first_link is
# awarded immediately by /link instead (see ADR-030), and the competition/
# community/tenure sets are awarded by their own events.
SNAPSHOT_EVALUATED: tuple[AchievementDef, ...] = (
    GAMES_100,
    GAMES_500,
    GAMES_1000,
    GAMES_2500,
    GAMES_5000,
    TIER_GOLD,
    TIER_PLATINUM,
    TIER_DIAMOND_PLUS,
    TIER_VALHALLAN,
    PEAK_1500,
    PEAK_1800,
    PEAK_2000,
    GLOBAL_TOP_1000,
    REGION_TOP_100,
    WIN_RATE_60,
)


def tier_index(tier: str) -> int | None:
    """This tier's position in _TIER_ORDER (higher = better), or None if
    unrecognized. Public — also used by services/snapshot_service.py to
    detect a tier promotion/demotion between two snapshots (docs/
    DECISIONS.md ADR-068), same "fails open, never raises" posture.
    """
    normalized = tier.strip().lower()
    for index, name in enumerate(_TIER_ORDER):
        if normalized.startswith(name):
            return index
    return None


def tier_at_least(tier: str | None, threshold: str) -> bool:
    """True if `tier` is at or above `threshold` in _TIER_ORDER. Fails open (False)."""
    if tier is None:
        return False
    index = tier_index(tier)
    if index is None:
        return False
    return index >= _TIER_ORDER.index(threshold)


def _newly_earned(
    thresholds: tuple[tuple[int, AchievementDef], ...],
    value: int | None,
    already_earned: set[str],
) -> list[AchievementDef]:
    """Every threshold at or below `value` that isn't already held."""
    if value is None:
        return []
    return [
        definition
        for threshold, definition in thresholds
        if value >= threshold and definition.key not in already_earned
    ]


def evaluate_snapshot_achievements(
    *,
    games: int,
    ranked_tier: str | None,
    already_earned: set[str],
    peak_rating: int | None = None,
    global_rank: int | None = None,
    region_rank: int | None = None,
    ranked_wins: int | None = None,
    ranked_games: int | None = None,
) -> tuple[AchievementDef, ...]:
    """Which of SNAPSHOT_EVALUATED are newly earned, given this cycle's stats.

    `games` is lifetime career games (the /player/{id}/stats counter);
    `ranked_wins`/`ranked_games` are the ranked-only pair used for the win
    rate. Every field past `already_earned` is optional so a caller with
    only partial data (or an older call site) still evaluates what it can.
    """
    earned: list[AchievementDef] = []
    earned.extend(_newly_earned(_GAMES_THRESHOLDS, games, already_earned))
    earned.extend(_newly_earned(_PEAK_THRESHOLDS, peak_rating, already_earned))

    for threshold_name, definition in _TIER_THRESHOLDS:
        if tier_at_least(ranked_tier, threshold_name) and definition.key not in already_earned:
            earned.append(definition)

    if (
        global_rank is not None
        and 0 < global_rank <= 1000
        and GLOBAL_TOP_1000.key not in already_earned
    ):
        earned.append(GLOBAL_TOP_1000)

    if (
        region_rank is not None
        and 0 < region_rank <= 100
        and REGION_TOP_100.key not in already_earned
    ):
        earned.append(REGION_TOP_100)

    if (
        ranked_games is not None
        and ranked_wins is not None
        and ranked_games >= MIN_RANKED_GAMES_FOR_WIN_RATE
        and ranked_wins / ranked_games >= 0.60
        and WIN_RATE_60.key not in already_earned
    ):
        earned.append(WIN_RATE_60)

    return tuple(earned)


def evaluate_competition_achievements(
    *,
    already_earned: set[str],
    match_wins: int | None = None,
    tournaments_entered: int | None = None,
    tournament_finals: int | None = None,
    tournament_wins: int | None = None,
    scrims_joined: int | None = None,
) -> tuple[AchievementDef, ...]:
    """Clan-internal competition milestones — matches, scrims, tournaments.

    None of this touches the Brawlhalla API; it's all the bot's own match
    bookkeeping (services/match_service.py, services/tournament_service.py).
    """
    earned: list[AchievementDef] = []
    earned.extend(_newly_earned(_MATCH_WIN_THRESHOLDS, match_wins, already_earned))

    if tournaments_entered and TOURNAMENT_ENTRANT.key not in already_earned:
        earned.append(TOURNAMENT_ENTRANT)
    if tournament_finals and TOURNAMENT_FINALIST.key not in already_earned:
        earned.append(TOURNAMENT_FINALIST)
    if tournament_wins and TOURNAMENT_CHAMPION.key not in already_earned:
        earned.append(TOURNAMENT_CHAMPION)
    if (
        scrims_joined is not None
        and scrims_joined >= 10
        and SCRIM_REGULAR.key not in already_earned
    ):
        earned.append(SCRIM_REGULAR)

    return tuple(earned)


def evaluate_engagement_achievements(
    *, already_earned: set[str], chat_level: int | None = None, mvp_weeks: int | None = None
) -> tuple[AchievementDef, ...]:
    """Community milestones from chat XP (services/chat_gamification.py) and
    the weekly MVP rotation (services/digest_service.py).
    """
    earned: list[AchievementDef] = []
    earned.extend(_newly_earned(_CHAT_LEVEL_THRESHOLDS, chat_level, already_earned))
    if mvp_weeks and MVP_OF_WEEK.key not in already_earned:
        earned.append(MVP_OF_WEEK)
    return tuple(earned)


def evaluate_tenure_achievements(
    *, days_in_clan: int | None, already_earned: set[str]
) -> tuple[AchievementDef, ...]:
    """Time-served milestones, measured from ShaheenMember.joined_at."""
    return tuple(_newly_earned(_TENURE_THRESHOLDS, days_in_clan, already_earned))


# Rarity bands for the website gallery, by share of the clan holding an
# achievement. Pure, and kept here with the rest of the achievement rules so
# the bot and the website can't drift on what "rare" means (ADR-081).
_RARITY_BANDS: tuple[tuple[float, str], ...] = (
    (50.0, "Common"),
    (25.0, "Uncommon"),
    (10.0, "Rare"),
    (0.0, "Legendary"),
)


def rarity_label(completion_pct: float) -> str:
    """Rarity band for a clan completion percentage.

    0% is "Unclaimed" rather than "Legendary" — nobody holding it says
    nothing about how hard it is, only that it hasn't happened yet.
    """
    if completion_pct <= 0:
        return "Unclaimed"
    for threshold, label in _RARITY_BANDS:
        if completion_pct >= threshold:
            return label
    return "Legendary"

"""ORM models. Import this module to register all models on Base.metadata."""

from database.models.achievement import Achievement
from database.models.base import Base
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.challenge import Challenge, ChallengeStatus
from database.models.chat_activity import ChatActivity
from database.models.discord_user import DiscordUser
from database.models.guild_settings import GuildSettings
from database.models.legend_snapshot import LegendSnapshot
from database.models.match import Match, MatchKind, MatchParticipant, MatchSide, MatchStatus
from database.models.member_achievement import MemberAchievement
from database.models.member_player_link import MemberPlayerLink
from database.models.provisioned_resource import ProvisionedResource, ResourceType
from database.models.ranking_snapshot import RankingSnapshot
from database.models.scrim import Scrim, ScrimSignup, ScrimStatus
from database.models.shaheen_member import ShaheenMember
from database.models.tournament import (
    Tournament,
    TournamentEntrant,
    TournamentEntrantMember,
    TournamentMatch,
    TournamentMatchStatus,
    TournamentStatus,
)
from database.models.warning import Warning

__all__ = [
    "Achievement",
    "Base",
    "BrawlhallaPlayer",
    "Challenge",
    "ChallengeStatus",
    "ChatActivity",
    "DiscordUser",
    "GuildSettings",
    "LegendSnapshot",
    "Match",
    "MatchKind",
    "MatchParticipant",
    "MatchSide",
    "MatchStatus",
    "MemberAchievement",
    "MemberPlayerLink",
    "ProvisionedResource",
    "RankingSnapshot",
    "ResourceType",
    "Scrim",
    "ScrimSignup",
    "ScrimStatus",
    "ShaheenMember",
    "Tournament",
    "TournamentEntrant",
    "TournamentEntrantMember",
    "TournamentMatch",
    "TournamentMatchStatus",
    "TournamentStatus",
    "Warning",
]

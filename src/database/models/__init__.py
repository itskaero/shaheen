"""ORM models. Import this module to register all models on Base.metadata."""

from database.models.achievement import Achievement
from database.models.application import Application, ApplicationStatus
from database.models.audit_log import AuditLogEntry
from database.models.base import Base
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.challenge import Challenge, ChallengeStatus
from database.models.chat_activity import ChatActivity
from database.models.coaching import Coach, CoachingRequest
from database.models.discord_user import DiscordUser
from database.models.guild_settings import GuildSettings
from database.models.guild_snapshot import GuildSnapshot
from database.models.legend_snapshot import LegendSnapshot
from database.models.link_code import LinkCode
from database.models.match import Match, MatchKind, MatchParticipant, MatchSide, MatchStatus
from database.models.member_achievement import MemberAchievement
from database.models.member_player_link import MemberPlayerLink
from database.models.pakistan_board_entry import PakistanBoardEntry
from database.models.player_report import PlayerReport
from database.models.provisioned_resource import ProvisionedResource, ResourceType
from database.models.ranking_snapshot import RankingSnapshot
from database.models.scrim import Scrim, ScrimSignup, ScrimStatus
from database.models.shaheen_member import ShaheenMember
from database.models.team import Team, TeamMember
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
    "Application",
    "ApplicationStatus",
    "AuditLogEntry",
    "Base",
    "BrawlhallaPlayer",
    "Challenge",
    "ChallengeStatus",
    "ChatActivity",
    "Coach",
    "CoachingRequest",
    "DiscordUser",
    "GuildSettings",
    "GuildSnapshot",
    "LegendSnapshot",
    "LinkCode",
    "Match",
    "MatchKind",
    "MatchParticipant",
    "MatchSide",
    "MatchStatus",
    "MemberAchievement",
    "MemberPlayerLink",
    "PakistanBoardEntry",
    "PlayerReport",
    "ProvisionedResource",
    "RankingSnapshot",
    "ResourceType",
    "Scrim",
    "ScrimSignup",
    "ScrimStatus",
    "ShaheenMember",
    "Team",
    "TeamMember",
    "Tournament",
    "TournamentEntrant",
    "TournamentEntrantMember",
    "TournamentMatch",
    "TournamentMatchStatus",
    "TournamentStatus",
    "Warning",
]

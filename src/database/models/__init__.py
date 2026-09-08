"""ORM models. Import this module to register all models on Base.metadata."""

from database.models.achievement import Achievement
from database.models.base import Base
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.discord_user import DiscordUser
from database.models.guild_settings import GuildSettings
from database.models.legend_snapshot import LegendSnapshot
from database.models.member_achievement import MemberAchievement
from database.models.member_player_link import MemberPlayerLink
from database.models.provisioned_resource import ProvisionedResource, ResourceType
from database.models.ranking_snapshot import RankingSnapshot
from database.models.shaheen_member import ShaheenMember

__all__ = [
    "Achievement",
    "Base",
    "BrawlhallaPlayer",
    "DiscordUser",
    "GuildSettings",
    "LegendSnapshot",
    "MemberAchievement",
    "MemberPlayerLink",
    "ProvisionedResource",
    "RankingSnapshot",
    "ResourceType",
    "ShaheenMember",
]

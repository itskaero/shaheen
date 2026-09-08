"""ORM models. Import this module to register all models on Base.metadata."""

from database.models.base import Base
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.discord_user import DiscordUser
from database.models.guild_settings import GuildSettings
from database.models.member_player_link import MemberPlayerLink
from database.models.provisioned_resource import ProvisionedResource, ResourceType
from database.models.shaheen_member import ShaheenMember

__all__ = [
    "Base",
    "BrawlhallaPlayer",
    "DiscordUser",
    "GuildSettings",
    "MemberPlayerLink",
    "ProvisionedResource",
    "ResourceType",
    "ShaheenMember",
]

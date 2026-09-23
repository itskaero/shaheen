# Database Specification

## Principles

The database stores persistent Shaheen state and historical data.
It must not be designed solely around Discord commands because the future
website will consume the same information.

## Initial conceptual entities

DiscordUser
- discord_id
- timestamps

ShaheenMember
- id
- discord_user_id
- status/role state
- joined_at
- timestamps

BrawlhallaPlayer
- id
- brawlhalla_player_id
- player_name
- region where applicable
- timestamps

MemberPlayerLink
- shaheen_member_id
- brawlhalla_player_id
- linked_at
- unlinked_at if history is required

PakistanBoardEntry (docs/DECISIONS.md ADR-099, migration 0011)
- guild_id
- brawlhalla_player_id (no member required — staff can add non-members)
- owner_discord_id (set when a member added themselves)
- added_by_discord_id
- added_at
- removed_at (soft delete; one active entry per player per guild)

RankingSnapshot
- player
- captured_at
- rating
- peak_rating
- tier
- wins
- losses
- rank/region where available
- season: the Brawlhalla season the reading belongs to (ADR-088). Derived from
  the date since ADR-102; migration 0015 restamped the rows production had
  stamped with the default "1" as S41 or S42

LegendSnapshot
- player
- captured_at
- legend identifier
- relevant statistics

Achievement
- stable achievement key
- name
- description

MemberAchievement
- member
- achievement
- awarded_at
- metadata if needed

GuildSettings
- guild_id
- setup_mode, last_setup_at
- announced_season: the last Brawlhalla season whose Pakistan Season start
  the bot posted (ADR-102, migration 0014)

Later:
Match
Challenge
Tournament
XPTransaction

## Constraints

- Use foreign keys and unique constraints.
- Store IDs, not display names, as relationships.
- Timestamps should be timezone-aware.
- Avoid storing unnecessary personal information.
- Use Alembic migrations.
- Do not silently change schema without a migration.

## History

Snapshots should be append-oriented. Do not overwrite historical records.

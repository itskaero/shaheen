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

RankingSnapshot
- player
- captured_at
- rating
- peak_rating
- tier
- wins
- losses
- rank/region where available

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

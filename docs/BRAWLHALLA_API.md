# Brawlhalla Integration Contract

## Purpose

Create an isolated Brawlhalla integration layer that can evolve independently
from Discord.

The official Brawlhalla Developer API is the external source for supported
player, ranking, Legend and clan/guild information.

Before implementation, verify current official API documentation rather than
assuming endpoint details from this document.

## Architecture

Discord command
  -> Shaheen service
  -> Brawlhalla service
  -> BrawlhallaClient
  -> external API

No cog should construct Brawlhalla URLs or perform HTTP requests directly.

## Initial data targets

Player identity:
- brawlhalla player ID
- player name

Ranked:
- rating
- peak rating
- tier
- wins
- losses
- region
- global rank where available

Legend:
- games
- wins
- KOs
- falls
- damage and other supported statistics

## Reliability

Implement:
- explicit HTTP timeout
- structured error handling
- rate-limit handling
- sensible retry behavior
- caching
- logging without secrets
- validation of API responses

Avoid unnecessary API calls.

## History

Current API data is not automatically clan history.
Shaheen must periodically snapshot relevant values into its own database so that
rating/progression history can later be displayed by Discord and the website.

## API-change resilience

Keep external response parsing/models separate from internal database/domain
models. Add tests around response parsing.

# Architecture

## High-level

Discord
  -> Commands / Views / Events
  -> Application Services
  -> Repositories / Integrations
  -> PostgreSQL / Brawlhalla API

Future:

Website
  -> Shaheen application/API layer
  -> same services/repositories
  -> same database

## Suggested package layout

src/
  main.py
  bot/
    client.py
    cogs/
    views/
    checks/
  core/
    config.py
    logging.py
    exceptions.py
  database/
    models/
    repositories/
    session.py
  services/
  integrations/
    brawlhalla/
      client.py
      models.py
      service.py
  utils/

tests/
docs/

## Rules

- Cogs are thin.
- Views handle interaction UI, not business logic.
- Services contain business rules.
- Repositories handle persistence.
- External APIs are accessed through integration clients/services.
- Configuration comes from environment/configuration objects.
- Use dependency injection lightly; do not build a framework.
- Async I/O throughout the bot.
- Cache external data where appropriate.

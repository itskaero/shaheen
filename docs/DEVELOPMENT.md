# Development Guide

## Local environment

Use a virtual environment and a .env file that is never committed.

Required configuration should include:
- DISCORD_TOKEN
- DATABASE_URL
- other integration settings as needed

## Quality

Run:
- Ruff format/check
- pytest
- type checks if configured

## Testing priorities

Unit-test:
- setup planning/idempotency
- permission decisions
- Brawlhalla response parsing
- service/business logic
- database repositories

Integration-test where practical:
- database migrations
- Discord setup against a disposable/test server

## Logging

Log:
- setup start/end
- important setup changes
- API failures
- command failures
- scheduled jobs

Do not log:
- tokens
- passwords
- database credentials
- unnecessary user data

## Git

Use small commits with meaningful messages.
Do not commit secrets, local databases, build artifacts or virtual environments.

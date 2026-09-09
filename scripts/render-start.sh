#!/bin/sh
# Render (free tier) start command for the shaheen-api web service.
#
# Why this is a script instead of a `dockerCommand: cmd1 && cmd2` one-liner
# (see docs/DECISIONS.md ADR-054): Render's dockerCommand field does not
# reliably shell-tokenize an inline string — a bare `&&` gets passed as a
# literal argument to the first command, and wrapping it in `sh -c "..."`
# was in turn swallowed whole and handed to `sh` as a single (space-and-all)
# command name. Baking the chain into a real script file and pointing
# dockerCommand at its path sidesteps whatever Render's own tokenizer does,
# since there's nothing left for it to split or requote.
#
# `alembic upgrade head` is idempotent (a no-op once already at head), so
# running it on every boot — every deploy and every wake from the free
# plan's idle sleep — is safe.
set -e

uv run alembic upgrade head
exec uv run uvicorn api.app:app --app-dir src --host 0.0.0.0 --port "$PORT"

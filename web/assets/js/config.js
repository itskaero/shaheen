// Shaheen website configuration.
//
// Set this to wherever the FastAPI backend (src/api/app.py) is deployed —
// see README.md's "Deploying the website" section. The Render free-tier
// blueprint (render.yaml) prints the URL to use here after the first
// deploy. Leave the localhost default for local development
// (`uv run uvicorn api.app:app --reload`).
const API_BASE_URL = "https://shaheen-api-6a6o.onrender.com";

// Optional: your Discord invite link (e.g. "https://discord.gg/xxxxxxx").
// Leave empty to hide the header's "Join Discord" button.
const DISCORD_INVITE_URL = "https://discord.gg/GTuQaE7WfF";

// Optional: your Discord server's numeric guild ID, used only to fetch the
// public, unauthenticated widget endpoint (discord.com/api/guilds/{id}/
// widget.json) for the live member/online-count badge (docs/DECISIONS.md
// ADR-066). Leave empty to hide the badge. Requires "Server Widget" to be
// enabled under Discord's Server Settings -> Widget — a portal toggle
// outside this repo; the badge just stays hidden if it's off or the guild
// ID below is wrong, it never breaks the page.
const DISCORD_GUILD_ID = "";

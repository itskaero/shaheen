// Shaheen website configuration.
//
// Where the FastAPI backend (src/api/app.py) is reachable: the NAS behind a
// Cloudflare Tunnel (docs/DEPLOY_NAS.md, ADR-127). For local development
// point it at http://localhost:8000 (`uv run uvicorn api.app:app --reload`).
const API_BASE_URL = "https://api.brawlistan.rekorex.online";

// Optional: your Discord invite link (e.g. "https://discord.gg/xxxxxxx").
// Leave empty to hide the header's "Join Discord" button.
const DISCORD_INVITE_URL = "https://discord.gg/UXVDWxBzy";

// Optional: your Discord server's numeric guild ID, used only to fetch the
// public, unauthenticated widget endpoint (discord.com/api/guilds/{id}/
// widget.json) for the live member/online-count badge (docs/DECISIONS.md
// ADR-066). Leave empty to hide the badge. Requires "Server Widget" to be
// enabled under Discord's Server Settings -> Widget — a portal toggle
// outside this repo; the badge just stays hidden if it's off or the guild
// ID below is wrong, it never breaks the page.
const DISCORD_GUILD_ID = "1546568759530229961";

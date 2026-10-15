"""The teams every BRAWLISTAN guild starts with (docs/DECISIONS.md ADR-127).

Migrations 0020 and 0023 seeded these, but only for guilds the database
already knew about, so a fresh database (the move to the NAS) came up with
no teams at all. The bot now makes sure they exist on every snapshot tick:
it creates a missing team and never touches one that's there, so staff edits
and deletions of anything else stand.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeedTeam:
    slug: str
    name: str
    tag: str
    accent: str
    accent_secondary: str
    clan_id: int | None = None
    description: str | None = None
    is_founding: bool = False


SEED_TEAMS: tuple[SeedTeam, ...] = (
    SeedTeam(
        "shaheen",
        "SHAHEEN",
        "SHN",
        "#3df26e",
        "#f0168c",
        description="The clan BRAWLISTAN grew out of. Pakistan's founding team.",
        is_founding=True,
    ),
    SeedTeam("delight-esports", "Delight Esports", "DE", "#e9c46a", "#1f6f8a", 2042085),
    SeedTeam("sigma-grinders", "Sigma Grinders", "SG", "#8b3dff", "#d9d4ff", 1777529),
    SeedTeam("revenant-wolf", "Revenant Wolf", "RW", "#e3122d", "#c7cad6", 2542774),
    SeedTeam("clan-monke", "Clan Monke", "MONKE", "#e8b923", "#2fbf4a", 1389219),
)

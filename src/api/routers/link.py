"""POST /link/claim — redeem a /link code on the website (docs/DECISIONS.md ADR-107).

The only write endpoint besides reports. Rate-limited per client, and every
failure about the code itself gets the same message, so the response never
helps someone guessing codes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.rate_limit import RateLimiter, client_ip
from core.config import Settings
from core.exceptions import ConflictError, InvalidCodeError, NotFoundError
from services.link_code_service import LinkCodeService

router = APIRouter(prefix="/link", tags=["link"])

# 10 attempts per 10 minutes per client. Codes are ~10^11 possibilities and
# live 15 minutes, so this makes guessing pointless.
claim_limiter = RateLimiter(limit=10, window_seconds=600)


class ClaimRequest(BaseModel):
    brawlhalla_id: int = Field(ge=1, le=10**12)
    code: str = Field(min_length=1, max_length=16)


class ClaimResponse(BaseModel):
    status: str
    player_name: str


@router.post("/claim", response_model=ClaimResponse)
async def claim_profile(
    body: ClaimRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ClaimResponse:
    claim_limiter.check(client_ip(request))
    try:
        outcome = await LinkCodeService(session).claim(
            guild_id=settings.guild_id, raw_code=body.code, brawlhalla_id=body.brawlhalla_id
        )
    except InvalidCodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc).replace("**", "")) from exc
    await session.commit()
    return ClaimResponse(status="linked", player_name=outcome.player.player_name)

# app/api/routes/match.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_async_session
from app.schemas.match import MatchRunRequest, MatchRunResponse, CandidateRow
from app.services.match.service import MatchService

router = APIRouter(prefix="/match", tags=["match"])

@router.post("/run", response_model=MatchRunResponse)
async def run_match(payload: MatchRunRequest, db: AsyncSession = Depends(get_async_session)):
    try:
        res = await MatchService.run(
            db, 
            payload.job_id, 
            payload.top_n, 
            payload.min_threshold
        )
        return MatchRunResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

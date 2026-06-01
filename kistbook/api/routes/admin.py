from __future__ import annotations

import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from kistbook.api.deps import get_current_user, get_db_session
from kistbook.core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


class TriggerScanRequest(BaseModel):
    retailer_id: Optional[uuid.UUID] = None


class TriggerScanResponse(BaseModel):
    tasks_enqueued: int
    customers_scanned: int
    scan_duration_ms: int


@router.post("/trigger-scan", response_model=TriggerScanResponse)
async def trigger_scan(
    body: TriggerScanRequest = TriggerScanRequest(),
    db: AsyncSession = Depends(get_db_session),
    _user: dict = Depends(get_current_user),
) -> TriggerScanResponse:
    if settings.ENVIRONMENT not in ("development", "test"):
        raise HTTPException(status_code=403, detail="Only available in development environment")

    from kistbook.engine.scanner import scan_all_retailers, scan_retailer

    start = time.monotonic()
    if body.retailer_id:
        result = await scan_retailer(db, body.retailer_id)
    else:
        result = await scan_all_retailers(db)

    duration_ms = int((time.monotonic() - start) * 1000)
    return TriggerScanResponse(
        tasks_enqueued=result["tasks_enqueued"],
        customers_scanned=result["customers_scanned"],
        scan_duration_ms=duration_ms,
    )

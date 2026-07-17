import json
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.finding import Finding
from app.routers.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/export", tags=["export"])


class ExportRequest(BaseModel):
    format: Literal["json", "pdf"] = "json"
    source_id: Optional[int] = None
    since: Optional[datetime] = None


@router.post("/findings")
async def export_findings(
    payload: ExportRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.format == "pdf":
        # PDF export is planned for v1.0 — requires reportlab or weasyprint
        return JSONResponse({"detail": "PDF export is coming in v1.0"}, status_code=501)

    stmt = select(Finding)
    if payload.source_id is not None:
        stmt = stmt.where(Finding.source_id == payload.source_id)
    if payload.since is not None:
        stmt = stmt.where(Finding.first_seen >= payload.since)
    stmt = stmt.order_by(Finding.first_seen.desc())

    findings = (await db.execute(stmt)).scalars().all()

    records = [
        {
            "id": f.id,
            "source_id": f.source_id,
            "url": f.url,
            "title": f.title,
            "content_snippet": f.content_snippet,
            "content_hash": f.content_hash,
            "matched_keywords": f.matched_keywords,
            "first_seen": f.first_seen.isoformat(),
            "last_seen": f.last_seen.isoformat(),
        }
        for f in findings
    ]

    content = json.dumps({"exported_at": datetime.utcnow().isoformat(), "count": len(records), "findings": records}, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=findings.json"},
    )

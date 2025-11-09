"""
API endpoints для краудрепортів (crowdreports)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import Optional

from database import get_db
from models.crowdreport import CrowdReport
from pydantic import BaseModel

router = APIRouter(prefix="/api/crowdreports", tags=["CrowdReports"])


class CrowdReportCreate(BaseModel):
    """Схема для створення краудрепорту"""
    user_id: int
    queue_id: int
    status: str  # "on" або "off"


class CrowdReportResponse(BaseModel):
    """Схема відповіді краудрепорту"""
    id: int
    user_id: int
    queue_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=CrowdReportResponse)
async def create_crowdreport(
        report_data: CrowdReportCreate,
        db: AsyncSession = Depends(get_db)
):
    """
    Створити новий краудрепорт про стан світла.

    Args:
        report_data: Дані репорту (user_id, queue_id, status)

    Returns:
        Створений краудрепорт
    """
    # Валідація статусу
    if report_data.status not in ["on", "off"]:
        raise HTTPException(status_code=400, detail="Status must be 'on' or 'off'")

    # Створити новий репорт
    new_report = CrowdReport(
        user_id=report_data.user_id,
        queue_id=report_data.queue_id,
        status=report_data.status
    )

    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)

    return new_report


@router.get("/stats")
async def get_crowdreport_stats(
        queue_id: int,
        minutes: int = 30,  # За останні N хвилин
        db: AsyncSession = Depends(get_db)
):
    """
    Отримати статистику краудрепортів для черги.

    Args:
        queue_id: ID черги
        minutes: Період часу (за замовчуванням 30 хвилин)

    Returns:
        Кількість репортів про увімкнення/відключення
    """
    since = datetime.utcnow() - timedelta(minutes=minutes)

    # Підрахувати репорти "світло є"
    on_count_result = await db.execute(
        select(func.count(CrowdReport.id))
        .where(
            CrowdReport.queue_id == queue_id,
            CrowdReport.status == "on",
            CrowdReport.created_at >= since
        )
    )
    on_count = on_count_result.scalar() or 0

    # Підрахувати репорти "світла немає"
    off_count_result = await db.execute(
        select(func.count(CrowdReport.id))
        .where(
            CrowdReport.queue_id == queue_id,
            CrowdReport.status == "off",
            CrowdReport.created_at >= since
        )
    )
    off_count = off_count_result.scalar() or 0

    return {
        "queue_id": queue_id,
        "on_count": on_count,
        "off_count": off_count,
        "period_minutes": minutes,
        "last_update": datetime.utcnow().isoformat()
    }


@router.get("/recent")
async def get_recent_reports(
        queue_id: Optional[int] = None,
        limit: int = 10,
        db: AsyncSession = Depends(get_db)
):
    """
    Отримати останні краудрепорти.

    Args:
        queue_id: Фільтр по черзі (опціонально)
        limit: Кількість репортів (за замовчуванням 10)

    Returns:
        Список останніх репортів
    """
    query = select(CrowdReport).order_by(CrowdReport.created_at.desc()).limit(limit)

    if queue_id:
        query = query.where(CrowdReport.queue_id == queue_id)

    result = await db.execute(query)
    reports = result.scalars().all()

    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "queue_id": r.queue_id,
            "status": r.status,
            "created_at": r.created_at.isoformat()
        }
        for r in reports
    ]


@router.get("/user/{user_id}")
async def get_user_reports(
        user_id: int,
        limit: int = 20,
        db: AsyncSession = Depends(get_db)
):
    """
    Отримати краудрепорти конкретного користувача.

    Args:
        user_id: Telegram ID користувача
        limit: Кількість репортів

    Returns:
        Список репортів користувача
    """
    result = await db.execute(
        select(CrowdReport)
        .where(CrowdReport.user_id == user_id)
        .order_by(CrowdReport.created_at.desc())
        .limit(limit)
    )
    reports = result.scalars().all()

    return [
        {
            "id": r.id,
            "queue_id": r.queue_id,
            "status": r.status,
            "created_at": r.created_at.isoformat()
        }
        for r in reports
    ]
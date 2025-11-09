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
    address_id: int  # ✅ ДОДАНО - обов'язкове поле
    queue_id: int
    report_type: str  # "power_on" або "power_off"


class CrowdReportResponse(BaseModel):
    """Схема відповіді краудрепорту"""
    id: int
    user_id: int
    address_id: int  # ✅ ДОДАНО
    queue_id: int
    report_type: str
    status: str
    reported_at: datetime  # ✅ ВИПРАВЛЕНО з created_at на reported_at

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
        report_data: Дані репорту (user_id, address_id, queue_id, report_type)

    Returns:
        Створений краудрепорт
    """
    # Валідація report_type
    if report_data.report_type not in ["power_on", "power_off"]:
        raise HTTPException(status_code=400, detail="report_type must be 'power_on' or 'power_off'")

    # Створити новий репорт
    new_report = CrowdReport(
        user_id=report_data.user_id,
        address_id=report_data.address_id,  # ✅ ДОДАНО
        queue_id=report_data.queue_id,
        report_type=report_data.report_type,
        status='pending'  # За замовчуванням pending
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
            CrowdReport.report_type == "power_on",
            CrowdReport.reported_at >= since
        )
    )
    on_count = on_count_result.scalar() or 0

    # Підрахувати репорти "світла немає"
    off_count_result = await db.execute(
        select(func.count(CrowdReport.id))
        .where(
            CrowdReport.queue_id == queue_id,
            CrowdReport.report_type == "power_off",
            CrowdReport.reported_at >= since
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
    query = select(CrowdReport).order_by(CrowdReport.reported_at.desc()).limit(limit)

    if queue_id:
        query = query.where(CrowdReport.queue_id == queue_id)

    result = await db.execute(query)
    reports = result.scalars().all()

    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "address_id": r.address_id,  # ✅ ДОДАНО
            "queue_id": r.queue_id,
            "report_type": r.report_type,
            "status": r.status,
            "reported_at": r.reported_at.isoformat()
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
        .order_by(CrowdReport.reported_at.desc())
        .limit(limit)
    )
    reports = result.scalars().all()

    return [
        {
            "id": r.id,
            "address_id": r.address_id,  # ✅ ДОДАНО
            "queue_id": r.queue_id,
            "report_type": r.report_type,
            "status": r.status,
            "reported_at": r.reported_at.isoformat()
        }
        for r in reports
    ]
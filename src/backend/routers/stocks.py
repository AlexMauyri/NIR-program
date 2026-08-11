from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import StockPrice

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/history")
async def get_stock_history(
    ticker: str = Query(default="SBER", description="Stock ticker"),
    date_from: date | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    date_to: date | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(default=1000, ge=1, le=10000, description="Max records"),
    offset: int = Query(default=0, ge=0, description="Skip records"),
    db: AsyncSession = Depends(get_db),
):
    query = select(StockPrice).where(StockPrice.ticker == ticker)

    if date_from:
        query = query.where(StockPrice.date >= date_from)
    if date_to:
        query = query.where(StockPrice.date <= date_to)

    query = query.order_by(StockPrice.date.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "ticker": ticker,
        "count": len(records),
        "offset": offset,
        "limit": limit,
        "data": [
            {
                "date": r.date.isoformat(),
                "open": float(r.open) if r.open else None,
                "high": float(r.high) if r.high else None,
                "low": float(r.low) if r.low else None,
                "close": float(r.close) if r.close else None,
            }
            for r in records
        ],
    }


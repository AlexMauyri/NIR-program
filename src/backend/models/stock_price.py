import datetime
from decimal import Decimal

from sqlalchemy import Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from models.base import Base

class StockPrice(Base):
    __tablename__ = "stock_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    date: Mapped[datetime.date] = mapped_column(nullable=False)

    open: Mapped[Decimal | None] = mapped_column(nullable=True)
    high: Mapped[Decimal | None] = mapped_column(nullable=True)
    low: Mapped[Decimal | None] = mapped_column(nullable=True)
    close: Mapped[Decimal | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("idx_stock_prices_ticker_date", "ticker", "date", unique=True),
    )

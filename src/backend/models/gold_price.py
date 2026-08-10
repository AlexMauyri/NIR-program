import datetime
from decimal import Decimal

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class GoldPrice(Base):
    __tablename__ = "gold_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.date] = mapped_column(nullable=False)

    open: Mapped[Decimal | None] = mapped_column(nullable=True)
    high: Mapped[Decimal | None] = mapped_column(nullable=True)
    low: Mapped[Decimal | None] = mapped_column(nullable=True)
    close: Mapped[Decimal | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("idx_gold_prices_date", "date", unique=True),
    )

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProductSent(Base):
    __tablename__ = "products_sent"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asin: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(500), nullable=True)
    preco_atual: Mapped[float] = mapped_column(Float, nullable=True)
    desconto_percentual: Mapped[float] = mapped_column(Float, nullable=True)
    categoria: Mapped[str] = mapped_column(String(100), nullable=True)
    group_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("asin", "group_id", name="uq_asin_group"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProductSent asin={self.asin!r} "
            f"desconto={self.desconto_percentual}% "
            f"sent_at={self.sent_at}>"
        )

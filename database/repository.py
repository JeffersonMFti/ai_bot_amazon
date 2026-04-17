import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from database.models import Base, ProductSent

logger = logging.getLogger(__name__)


@dataclass
class ProductData:
    asin: str
    titulo: str
    preco_atual: float
    desconto_percentual: float
    categoria: str


class ProductRepository:
    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self._engine)

    def filtrar_ja_enviados(
        self,
        asins: List[str],
        group_id: str,
        dias: int = 30,
    ) -> List[str]:
        """Retorna os ASINs da lista que NÃO foram enviados nos últimos N dias."""
        if not asins:
            return []

        desde = datetime.utcnow() - timedelta(days=dias)

        with Session(self._engine) as session:
            stmt = select(ProductSent.asin).where(
                ProductSent.asin.in_(asins),
                ProductSent.group_id == group_id,
                ProductSent.sent_at >= desde,
            )
            enviados = {row for row in session.scalars(stmt)}

        novos = [asin for asin in asins if asin not in enviados]
        logger.debug(
            "filtrar_ja_enviados: %d recebidos, %d já enviados, %d novos",
            len(asins),
            len(enviados),
            len(novos),
        )
        return novos

    def registrar_enviado(self, produto: ProductData, group_id: str) -> None:
        """Registra que um produto foi enviado para o grupo."""
        with Session(self._engine) as session:
            registro = ProductSent(
                asin=produto.asin,
                titulo=produto.titulo,
                preco_atual=produto.preco_atual,
                desconto_percentual=produto.desconto_percentual,
                categoria=produto.categoria,
                group_id=group_id,
            )
            session.merge(registro)
            session.commit()
            logger.debug("Produto registrado no banco: asin=%s", produto.asin)

    def listar_enviados_recentes(
        self, group_id: str, limit: int = 50
    ) -> List[ProductSent]:
        """Retorna os últimos N produtos enviados para o grupo."""
        with Session(self._engine) as session:
            stmt = (
                select(ProductSent)
                .where(ProductSent.group_id == group_id)
                .order_by(ProductSent.sent_at.desc())
                .limit(limit)
            )
            return list(session.scalars(stmt))

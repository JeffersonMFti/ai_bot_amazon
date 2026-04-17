import logging
import time
from dataclasses import dataclass
from typing import List, Optional

from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.get_items_request import GetItemsRequest
from paapi5_python_sdk.models.get_items_resource import GetItemsResource
from paapi5_python_sdk.models.partner_type import PartnerType
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from paapi5_python_sdk.rest import ApiException

from config import AmazonConfig

logger = logging.getLogger(__name__)

# Recursos que queremos trazer da PA API
_SEARCH_RESOURCES = [
    SearchItemsResource.ITEMINFO_TITLE,
    SearchItemsResource.OFFERS_LISTINGS_PRICE,
    SearchItemsResource.OFFERS_LISTINGS_SAVINGBASIS,
    SearchItemsResource.OFFERS_LISTINGS_PROMOTIONS,
    SearchItemsResource.CUSTOMERREVIEWS_STARRATING,
    SearchItemsResource.CUSTOMERREVIEWS_COUNT,
    SearchItemsResource.ITEMINFO_CLASSIFICATIONS,
    SearchItemsResource.IMAGES_PRIMARY_LARGE,
]

# Categorias de beleza feminina mapeadas para browse nodes
CATEGORIAS_BELEZA = {
    "geral": None,          # busca geral em Beauty
    "maquiagem": None,
    "skincare": None,
    "cabelo": None,
    "perfume": None,
}


@dataclass
class Produto:
    asin: str
    titulo: str
    preco_atual: float
    preco_original: Optional[float]
    desconto_percentual: float
    avaliacao: float
    num_reviews: int
    url_afiliado: str
    categoria: str
    imagem_url: Optional[str] = None


class AmazonService:
    def __init__(self, config: AmazonConfig) -> None:
        self._config = config
        self._api = DefaultApi(
            access_key=config.access_key,
            secret_key=config.secret_key,
            host="webservices.amazon.com.br",
            region="us-east-1",
        )

    def buscar_promocoes_beleza(
        self,
        limite: int = 10,
        min_desconto: float = 20.0,
        min_avaliacao: float = 4.0,
        min_reviews: int = 50,
    ) -> List[Produto]:
        """Busca produtos de beleza feminina em promoção e retorna lista filtrada."""
        produtos: List[Produto] = []

        for tentativa in range(3):
            try:
                request = SearchItemsRequest(
                    partner_tag=self._config.partner_tag,
                    partner_type=PartnerType.ASSOCIATES,
                    keywords="beleza feminina maquiagem skincare perfume",
                    search_index="Beauty",
                    item_count=limite,
                    min_saving_percent=int(min_desconto),
                    resources=_SEARCH_RESOURCES,
                )
                resposta = self._api.search_items(request)
                break
            except ApiException as exc:
                if exc.status == 429:  # ThrottlingException
                    espera = 2 ** tentativa
                    logger.warning(
                        "Amazon API throttling — aguardando %ds (tentativa %d/3)",
                        espera,
                        tentativa + 1,
                    )
                    time.sleep(espera)
                    if tentativa == 2:
                        logger.error("Amazon API: limite de tentativas atingido.")
                        return []
                else:
                    logger.error("Amazon API erro %s: %s", exc.status, exc.reason)
                    return []

        if not resposta.search_result or not resposta.search_result.items:
            logger.info("Amazon API: nenhum produto encontrado na busca.")
            return []

        for item in resposta.search_result.items:
            produto = self._parse_item(item)
            if produto is None:
                continue
            if produto.desconto_percentual < min_desconto:
                continue
            if produto.avaliacao < min_avaliacao:
                continue
            if produto.num_reviews < min_reviews:
                continue
            produtos.append(produto)

        produtos.sort(
            key=lambda p: (p.desconto_percentual, p.avaliacao), reverse=True
        )

        logger.info(
            "Amazon: %d produtos encontrados após filtros.",
            len(produtos),
        )
        return produtos

    def _parse_item(self, item) -> Optional[Produto]:
        try:
            asin = item.asin
            titulo = item.item_info.title.display_value

            ofertas = item.offers.listings[0] if item.offers and item.offers.listings else None
            if not ofertas or not ofertas.price:
                return None

            preco_atual = ofertas.price.amount
            preco_original = None
            desconto_percentual = 0.0

            if ofertas.saving_basis:
                preco_original = ofertas.saving_basis.amount
                if preco_original and preco_original > preco_atual:
                    desconto_percentual = round(
                        (1 - preco_atual / preco_original) * 100, 1
                    )

            avaliacao = 0.0
            num_reviews = 0
            if item.customer_reviews:
                if item.customer_reviews.star_rating:
                    avaliacao = item.customer_reviews.star_rating.value or 0.0
                if item.customer_reviews.count:
                    num_reviews = item.customer_reviews.count.value or 0

            imagem_url = None
            if item.images and item.images.primary and item.images.primary.large:
                imagem_url = item.images.primary.large.url

            categoria = "beleza"
            if item.item_info.classifications:
                categoria = (
                    item.item_info.classifications.product_group.display_value
                    or "beleza"
                )

            url_afiliado = (
                f"https://www.amazon.com.br/dp/{asin}"
                f"?tag={self._config.partner_tag}"
            )

            return Produto(
                asin=asin,
                titulo=titulo,
                preco_atual=preco_atual,
                preco_original=preco_original,
                desconto_percentual=desconto_percentual,
                avaliacao=avaliacao,
                num_reviews=num_reviews,
                url_afiliado=url_afiliado,
                categoria=categoria,
                imagem_url=imagem_url,
            )

        except (AttributeError, TypeError, IndexError) as exc:
            logger.debug("Erro ao parsear item: %s", exc)
            return None

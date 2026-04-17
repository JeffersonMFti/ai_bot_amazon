import logging
import logging.handlers
import os
import signal
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import load_config
from database.repository import ProductRepository, ProductData
from services.amazon import AmazonService
from services.openai_copy import OpenAICopyService
from services.whatsapp import WhatsAppService
from utils.formatter import formatar_mensagem

_DELAY_ENTRE_PRODUTOS = 180  # segundos — alinhado com AGENT_RULES.md


def configurar_logging(log_level: str, log_file: str) -> None:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s]  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        handlers=[console_handler, file_handler],
    )


def criar_job(
    amazon: AmazonService,
    openai_copy: OpenAICopyService,
    whatsapp: WhatsAppService,
    repositorio: ProductRepository,
    group_id: str,
    max_produtos: int,
    min_desconto: float,
    min_avaliacao: float,
    nome_job: str,
):
    logger = logging.getLogger(__name__)

    def job():
        logger.info("job=%s | Iniciando busca de promoções", nome_job)

        produtos = amazon.buscar_promocoes_beleza(
            limite=20,
            min_desconto=min_desconto,
            min_avaliacao=min_avaliacao,
        )

        if not produtos:
            logger.info("job=%s | Nenhum produto encontrado. Encerrando.", nome_job)
            return

        asins_candidatos = [p.asin for p in produtos]
        asins_novos = repositorio.filtrar_ja_enviados(asins_candidatos, group_id)

        produtos_novos = [p for p in produtos if p.asin in asins_novos]

        if not produtos_novos:
            logger.info(
                "job=%s | Todos os %d produtos já foram enviados recentemente.",
                nome_job,
                len(produtos),
            )
            return

        selecionados = produtos_novos[:max_produtos]
        logger.info(
            "job=%s | Encontrados %d novos. Enviando %d produto(s).",
            nome_job,
            len(produtos_novos),
            len(selecionados),
        )

        enviados = 0
        for i, produto in enumerate(selecionados):
            logger.info(
                "job=%s | [%d/%d] ASIN=%s | %.0f%% OFF | R$ %.2f",
                nome_job,
                i + 1,
                len(selecionados),
                produto.asin,
                produto.desconto_percentual,
                produto.preco_atual,
            )

            copy = openai_copy.gerar(produto)
            mensagem = formatar_mensagem(copy, produto.url_afiliado)
            sucesso = whatsapp.enviar_grupo(mensagem)

            if sucesso:
                repositorio.registrar_enviado(
                    ProductData(
                        asin=produto.asin,
                        titulo=produto.titulo,
                        preco_atual=produto.preco_atual,
                        desconto_percentual=produto.desconto_percentual,
                        categoria=produto.categoria,
                    ),
                    group_id=group_id,
                )
                enviados += 1
            else:
                logger.error(
                    "job=%s | Falha ao enviar ASIN=%s — não registrado no banco.",
                    nome_job,
                    produto.asin,
                )

            if i < len(selecionados) - 1:
                time.sleep(_DELAY_ENTRE_PRODUTOS)

        logger.info(
            "job=%s | Concluído. %d/%d produto(s) enviado(s).",
            nome_job,
            enviados,
            len(selecionados),
        )

    return job


def main() -> None:
    config = load_config()
    configurar_logging(config.log_level, config.log_file)
    logger = logging.getLogger(__name__)

    logger.info("Iniciando Amazon Affiliate Bot...")

    repositorio = ProductRepository(config.database_url)
    amazon = AmazonService(config.amazon)
    openai_copy = OpenAICopyService(config.openai)
    whatsapp = WhatsAppService(config.uazapi)

    kwargs_job = dict(
        amazon=amazon,
        openai_copy=openai_copy,
        whatsapp=whatsapp,
        repositorio=repositorio,
        group_id=config.uazapi.group_id,
        max_produtos=config.bot.max_products_per_send,
        min_desconto=config.bot.min_discount_percent,
        min_avaliacao=config.bot.min_rating,
    )

    job_diario = criar_job(**kwargs_job, nome_job="diario")

    scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    scheduler.add_job(
        job_diario,
        CronTrigger(hour=config.bot.send_hour, minute=0),
        id="job_diario",
        name="Envio Diário",
    )

    scheduler.start()
    logger.info(
        "Scheduler ativo. Envio programado: %dh (Horário de Brasília).",
        config.bot.send_hour,
    )

    def shutdown(signum, frame):
        logger.info("Sinal de encerramento recebido. Finalizando scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=False)
        logger.info("Bot encerrado.")


if __name__ == "__main__":
    main()

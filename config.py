import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Variável de ambiente obrigatória não encontrada: '{key}'. "
            f"Verifique o arquivo .env."
        )
    return value


def _optional(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass(frozen=True)
class AmazonConfig:
    access_key: str
    secret_key: str
    partner_tag: str
    country: str


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str


@dataclass(frozen=True)
class UazapiConfig:
    base_url: str
    token: str
    admintoken: str
    group_id: str


@dataclass(frozen=True)
class BotConfig:
    send_hour: int
    max_products_per_send: int
    min_discount_percent: float
    min_rating: float
    days_before_resend: int


@dataclass(frozen=True)
class AppConfig:
    amazon: AmazonConfig
    openai: OpenAIConfig
    uazapi: UazapiConfig
    bot: BotConfig
    database_url: str
    log_level: str
    log_file: str


def load_config() -> AppConfig:
    return AppConfig(
        amazon=AmazonConfig(
            access_key=_require("AMAZON_ACCESS_KEY"),
            secret_key=_require("AMAZON_SECRET_KEY"),
            partner_tag=_require("AMAZON_PARTNER_TAG"),
            country=_optional("AMAZON_COUNTRY", "BR"),
        ),
        openai=OpenAIConfig(
            api_key=_require("OPENAI_API_KEY"),
            model=_optional("OPENAI_MODEL", "gpt-4o-mini"),
        ),
        uazapi=UazapiConfig(
            base_url=_require("UAZAPI_BASE_URL"),
            token=_require("UAZAPI_TOKEN"),
            admintoken=_optional("UAZAPI_ADMINTOKEN", ""),
            group_id=_require("WHATSAPP_GROUP_ID"),
        ),
        bot=BotConfig(
            send_hour=int(_optional("SEND_HOUR", "20")),
            max_products_per_send=int(_optional("MAX_PRODUCTS_PER_SEND", "3")),
            min_discount_percent=float(_optional("MIN_DISCOUNT_PERCENT", "20")),
            min_rating=float(_optional("MIN_RATING", "4.0")),
            days_before_resend=int(_optional("DAYS_BEFORE_RESEND", "30")),
        ),
        database_url=_optional("DATABASE_URL", "sqlite:///./data/bot.db"),
        log_level=_optional("LOG_LEVEL", "INFO"),
        log_file=_optional("LOG_FILE", "./logs/bot.log"),
    )

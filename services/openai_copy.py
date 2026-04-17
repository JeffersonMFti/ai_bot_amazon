import logging
import os
from pathlib import Path
from typing import Optional

from openai import OpenAI, APIError, APITimeoutError

from config import OpenAIConfig
from services.amazon import Produto

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Copy de fallback usada se o GPT falhar
_FALLBACK_COPY = (
    "✨ Oferta incrível de beleza na Amazon!\n\n"
    "{titulo}\n"
    "💰 De R$ {preco_original} por R$ {preco_atual} ({desconto}% OFF)\n"
    "⭐ {avaliacao} estrelas\n\n"
    "👉 Aproveita antes acabar:\n{link}"
)

_SYSTEM_PROMPT = """Você é Bella, uma amiga especialista em beleza que indica produtos incríveis \
para um grupo de mulheres no WhatsApp.

Seu objetivo é criar uma mensagem curta, animada e persuasiva para indicar \
um produto de beleza em promoção na Amazon, incentivando as mulheres do \
grupo a comprarem usando o link fornecido.

REGRAS OBRIGATÓRIAS:
- Escreva em português brasileiro informal e próximo
- Máximo de 6 linhas no total
- Use 3 a 5 emojis relevantes, distribuídos na mensagem
- Destaque o desconto e o preço atual
- Termine SEMPRE com o link do produto na última linha
- NUNCA invente informações além das fornecidas
- NUNCA faça afirmações médicas ou prometa resultados garantidos
- NUNCA use linguagem de urgência falsa
- Tom: animado, feminino, genuíno — como uma amiga indicando algo que amou"""


class OpenAICopyService:
    def __init__(self, config: OpenAIConfig) -> None:
        self._client = OpenAI(api_key=config.api_key)
        self._model = config.model

    def gerar(self, produto: Produto) -> str:
        """Gera copy persuasiva para o produto. Retorna fallback se a API falhar."""
        prompt_usuario = self._montar_prompt(produto)

        try:
            resposta = self._client.chat.completions.create(
                model=self._model,
                max_tokens=300,
                temperature=0.8,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_usuario},
                ],
            )
            copy = resposta.choices[0].message.content.strip()
            logger.info("Copy gerada via GPT para asin=%s", produto.asin)
            return copy

        except (APIError, APITimeoutError) as exc:
            logger.warning(
                "OpenAI API falhou para asin=%s: %s — usando fallback",
                produto.asin,
                exc,
            )
            return self._fallback(produto)

    def _montar_prompt(self, produto: Produto) -> str:
        preco_original = (
            f"R$ {produto.preco_original:.2f}".replace(".", ",")
            if produto.preco_original
            else "preço original não disponível"
        )
        preco_atual = f"R$ {produto.preco_atual:.2f}".replace(".", ",")

        return (
            f"Produto: {produto.titulo}\n"
            f"Preço original: {preco_original}\n"
            f"Preço atual: {preco_atual}\n"
            f"Desconto: {produto.desconto_percentual:.0f}%\n"
            f"Avaliação: {produto.avaliacao} estrelas "
            f"({produto.num_reviews} avaliações)\n"
            f"Categoria: {produto.categoria}\n"
            f"Link de compra: {produto.url_afiliado}\n\n"
            "Crie a mensagem para o grupo de beleza seguindo as regras."
        )

    def _fallback(self, produto: Produto) -> str:
        preco_original = (
            f"{produto.preco_original:.2f}".replace(".", ",")
            if produto.preco_original
            else "—"
        )
        preco_atual = f"{produto.preco_atual:.2f}".replace(".", ",")

        return _FALLBACK_COPY.format(
            titulo=produto.titulo,
            preco_original=preco_original,
            preco_atual=preco_atual,
            desconto=int(produto.desconto_percentual),
            avaliacao=produto.avaliacao,
            link=produto.url_afiliado,
        )

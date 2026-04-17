import logging
import time

import httpx

from config import UazapiConfig

logger = logging.getLogger(__name__)

_TIMEOUT = 15  # segundos
_MAX_RETRIES = 2
_RETRY_DELAY = 10  # segundos entre tentativas


class WhatsAppService:
    def __init__(self, config: UazapiConfig) -> None:
        self._base_url = config.base_url.rstrip("/")
        self._headers = {
            "token": config.token,
            "Content-Type": "application/json",
        }
        self._group_id = config.group_id

    def esta_conectado(self) -> bool:
        """Verifica se a instância UAZAPI está conectada ao WhatsApp."""
        url = f"{self._base_url}/instance/status"
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resposta = client.get(url, headers=self._headers)
            if resposta.status_code == 200:
                dados = resposta.json()
                status = dados.get("status", "")
                if status == "connected":
                    return True
                logger.warning("UAZAPI status: %s", status)
        except httpx.RequestError as exc:
            logger.warning("UAZAPI erro ao verificar status: %s", exc)
        return False

    def enviar_grupo(self, mensagem: str) -> bool:
        """
        Envia uma mensagem de texto para o grupo WhatsApp configurado.
        Retorna True em caso de sucesso, False em caso de falha definitiva.
        """
        payload = {
            "number": self._group_id,
            "text": mensagem,
        }
        url = f"{self._base_url}/send/text"

        for tentativa in range(1, _MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=_TIMEOUT) as client:
                    resposta = client.post(url, json=payload, headers=self._headers)

                if resposta.status_code in (200, 201):
                    dados = resposta.json()
                    msg_id = dados.get("id", "desconhecido")
                    logger.info("WhatsApp ACK: msg_id=%s", msg_id)
                    return True

                logger.warning(
                    "UAZAPI retornou status %d (tentativa %d/%d): %s",
                    resposta.status_code,
                    tentativa,
                    _MAX_RETRIES,
                    resposta.text[:200],
                )

            except httpx.TimeoutException:
                logger.warning(
                    "UAZAPI timeout (tentativa %d/%d)", tentativa, _MAX_RETRIES
                )
            except httpx.RequestError as exc:
                logger.warning(
                    "UAZAPI erro de conexão (tentativa %d/%d): %s",
                    tentativa,
                    _MAX_RETRIES,
                    exc,
                )

            if tentativa < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)

        logger.error(
            "UAZAPI: falha definitiva ao enviar mensagem para o grupo %s após %d tentativas.",
            self._group_id,
            _MAX_RETRIES,
        )
        return False

    def enviar_grupo_com_midia(self, mensagem: str, imagem_url: str) -> bool:
        """
        Envia imagem + legenda para o grupo WhatsApp via POST /send/media.
        Caso a imagem_url seja vazia ou o envio falhe, faz fallback para
        enviar_grupo() com o texto puro.
        Retorna True em caso de sucesso, False em caso de falha definitiva.
        """
        if not imagem_url:
            logger.debug("imagem_url vazia — usando envio de texto puro.")
            return self.enviar_grupo(mensagem)

        payload = {
            "number": self._group_id,
            "mediatype": "image",
            "media": imagem_url,
            "caption": mensagem,
        }
        url = f"{self._base_url}/send/media"

        for tentativa in range(1, _MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=_TIMEOUT) as client:
                    resposta = client.post(url, json=payload, headers=self._headers)

                if resposta.status_code in (200, 201):
                    dados = resposta.json()
                    msg_id = dados.get("id", "desconhecido")
                    logger.info("WhatsApp ACK (mídia): msg_id=%s", msg_id)
                    return True

                logger.warning(
                    "UAZAPI /send/media retornou status %d (tentativa %d/%d): %s",
                    resposta.status_code,
                    tentativa,
                    _MAX_RETRIES,
                    resposta.text[:200],
                )

            except httpx.TimeoutException:
                logger.warning(
                    "UAZAPI /send/media timeout (tentativa %d/%d)", tentativa, _MAX_RETRIES
                )
            except httpx.RequestError as exc:
                logger.warning(
                    "UAZAPI /send/media erro de conexão (tentativa %d/%d): %s",
                    tentativa,
                    _MAX_RETRIES,
                    exc,
                )

            if tentativa < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)

        logger.warning(
            "UAZAPI: falha ao enviar mídia para %s — fazendo fallback para texto puro.",
            self._group_id,
        )
        return self.enviar_grupo(mensagem)

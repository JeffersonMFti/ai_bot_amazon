_LIMITE_WHATSAPP = 4096


def formatar_mensagem(copy: str, url_afiliado: str) -> str:
    """
    Garante que a mensagem final sempre contém o link de afiliado.
    Se o GPT já incluiu o link na copy, não duplica.
    Trunca a mensagem se ultrapassar o limite do WhatsApp.
    """
    if url_afiliado not in copy:
        mensagem = f"{copy}\n\n👉 {url_afiliado}"
    else:
        mensagem = copy

    if len(mensagem) > _LIMITE_WHATSAPP:
        mensagem = mensagem[: _LIMITE_WHATSAPP - 3] + "..."

    return mensagem.strip()

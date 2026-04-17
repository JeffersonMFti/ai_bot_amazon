# Arquitetura — AI Bot Amazon (Afiliado Beleza Feminina)

Documento técnico completo da arquitetura do sistema de afiliado automatizado.

---

## 1. Visão Geral do Sistema

O sistema é composto por um processo Python contínuo rodando em VPS, que executa um scheduler para disparar o fluxo de envio **1x ao dia**. Cada execução percorre um pipeline linear: **busca → filtro → geração de copy → envio**.

```
┌─────────────────────────────────────────────────────────┐
│                    VPS Hetzner CX22                     │
│                    Ubuntu 24.04 LTS                     │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Docker Compose Stack               │   │
│  │                                                 │   │
│  │   ┌───────────────┐    ┌──────────────────┐    │   │
│  │   │   bot         │    │   uazapi         │    │   │
│  │   │   (Python)    │───▶│   (WhatsApp API) │    │   │
│  │   │   Port: —     │    │   Port: 3000     │    │   │
│  │   └──────┬────────┘    └──────────────────┘    │   │
│  │          │                                      │   │
│  │   ┌──────▼────────┐                            │   │
│  │   │   SQLite DB   │                            │   │
│  │   │   (volume)    │                            │   │
│  │   └───────────────┘                            │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
          │                           │
          ▼                           ▼
   Amazon PA API              OpenAI API
   (produtos/preços)          (geração de copy)
```

---

## 2. Fluxo de Execução (Pipeline)

O scheduler dispara o job `enviar_promocoes()` nos horários configurados:

```
TRIGGER (APScheduler — 20h BRT, padrão configurável)
        │
        ▼
[1] amazon.buscar_promocoes_beleza()
        │  Retorna: Lista<Produto>
        │  Campos: ASIN, título, preço_original, preço_atual,
        │          desconto_%, avaliação, num_reviews, URL, imagem
        ▼
[2] db.filtrar_ja_enviados(produtos)
        │  Remove ASINs já registrados no banco (últimos 30 dias)
        │  Retorna: Lista<Produto> (apenas novos)
        ▼
[3] Selecionar top N produtos
        │  Ordenar por: desconto_% DESC, avaliação DESC
        │  Limite: MAX_PRODUCTS_PER_SEND (padrão: 3)
        ▼
[4] Para cada produto:
        │
        ├── openai_copy.gerar(produto)
        │       Retorna: texto persuasivo com CTA
        │
        ├── formatter.montar_mensagem(produto, copy)
        │       Retorna: mensagem final formatada
        │
        ├── whatsapp.enviar_grupo(mensagem)
        │       POST /message/sendText → UAZAPI
        │
        ├── db.registrar_enviado(produto.asin)
        │       Salva no banco para evitar reenvio
        │
        └── sleep(180s)  ← delay anti-spam entre produtos
```

---

## 3. Componentes e Responsabilidades

### 3.1 `main.py` — Entrypoint e Scheduler

```
Responsabilidades:
  - Inicializar o APScheduler (BackgroundScheduler)
  - Registrar os jobs de envio com horários configuráveis
  - Manter o processo vivo (blocking)
  - Capturar SIGTERM/SIGINT para shutdown gracioso

Jobs registrados:
  - job_diario: cron hour=SEND_HOUR, minute=0
  - Timezone: America/Sao_Paulo
```

### 3.2 `config.py` — Configuração Centralizada

```
Responsabilidades:
  - Carregar variáveis do .env via python-dotenv
  - Validar presença de variáveis obrigatórias na inicialização
  - Expor constantes tipadas para o restante do sistema
  - Lançar erro claro se variável obrigatória estiver ausente

Variáveis gerenciadas:
  Amazon: ACCESS_KEY, SECRET_KEY, PARTNER_TAG, COUNTRY
  OpenAI: API_KEY, MODEL
  UAZAPI: BASE_URL, TOKEN, GROUP_ID
  Bot:    SEND_HOUR,
          MAX_PRODUCTS_PER_SEND, MIN_DISCOUNT_PERCENT, MIN_RATING
```

### 3.3 `services/amazon.py` — Integração Amazon PA API

```
Responsabilidades:
  - Autenticar na Amazon PA API 5.0
  - Buscar produtos por categoria (Beauty)
  - Filtrar por desconto mínimo e avaliação mínima
  - Montar URL com Partner Tag (link de afiliado)
  - Retornar lista de objetos Produto normalizados

Categorias suportadas:
  - Beauty (geral)
  - Maquiagem: SkinCare → Makeup
  - Skincare: SkinCare
  - Cabelo: HairCare
  - Perfume: FragranceWomen

Campos retornados por produto:
  - asin: str
  - titulo: str
  - preco_original: float | None
  - preco_atual: float
  - desconto_percentual: float
  - avaliacao: float
  - num_reviews: int
  - url_afiliado: str
  - categoria: str

Tratamento de erros:
  - ThrottlingException → retry com backoff exponencial (3x)
  - ItemNotAccessibleException → ignorar produto
  - Timeout (10s) → logar e continuar
```

### 3.4 `services/openai_copy.py` — Geração de Copy

```
Responsabilidades:
  - Montar prompt com dados do produto
  - Chamar GPT-4o-mini via OpenAI API
  - Retornar texto pronto para uso no WhatsApp
  - Fallback: copy padrão sem IA se API falhar

Parâmetros da chamada:
  - model: gpt-4o-mini
  - max_tokens: 300
  - temperature: 0.8
  - system prompt: contexto de afiliada de beleza feminina

Estrutura do prompt enviado ao GPT:
  - Nome do produto
  - Preço original e promocional
  - Percentual de desconto
  - Avaliação e número de reviews
  - Categoria
  - Instrução de tom: animado, feminino, persuasivo, emoji estratégicos
  - Instrução de limite: máximo 5 linhas + CTA + link
```

### 3.5 `services/whatsapp.py` — Envio via UAZAPI

```
Responsabilidades:
  - Enviar mensagem de texto para o grupo WhatsApp
  - Autenticar chamadas com token UAZAPI
  - Tratar erros de envio (retry 2x com delay)

Endpoint utilizado:
  POST {UAZAPI_BASE_URL}/message/sendText
  Headers: Authorization: Bearer {UAZAPI_TOKEN}
  Body: {
    "chatId": "{WHATSAPP_GROUP_ID}",
    "text": "{mensagem}"
  }

Validações:
  - Verificar resposta HTTP 200/201
  - Logar ID da mensagem retornado pelo UAZAPI
  - Em caso de falha: logar erro, NÃO registrar produto no banco
```

### 3.6 `database/` — Persistência

```
Banco: SQLite (arquivo local em volume Docker)
ORM: SQLAlchemy 2.x

Tabela: products_sent
  - id: INTEGER PRIMARY KEY AUTOINCREMENT
  - asin: VARCHAR(20) NOT NULL
  - titulo: VARCHAR(500)
  - preco_atual: FLOAT
  - desconto_percentual: FLOAT
  - sent_at: DATETIME DEFAULT CURRENT_TIMESTAMP
  - group_id: VARCHAR(100)  ← para suportar múltiplos grupos futuramente

Índices:
  - UNIQUE(asin, group_id) para evitar duplicatas
  
Queries principais:
  - filtrar_ja_enviados(asins, group_id, dias=30)
  - registrar_enviado(produto, group_id)
  - listar_enviados_recentes(group_id, limit=50)
```

### 3.7 `utils/formatter.py` — Formatação de Mensagem

```
Responsabilidades:
  - Combinar copy do GPT com estrutura padrão
  - Adicionar cabeçalho e rodapé fixos
  - Garantir que o link afiliado sempre está presente
  - Truncar mensagem se ultrapassar limite do WhatsApp (4096 chars)

Estrutura da mensagem final:
  [CABEÇALHO — emoji + título da oferta]
  [COPY DO GPT — texto persuasivo]
  [URL DO AFILIADO]
  [RODAPÉ — aviso de promoção por tempo limitado]
```

---

## 4. Modelo de Dados

### Tabela `products_sent`

```sql
CREATE TABLE products_sent (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    asin                VARCHAR(20)  NOT NULL,
    titulo              VARCHAR(500),
    preco_atual         FLOAT,
    desconto_percentual FLOAT,
    categoria           VARCHAR(100),
    group_id            VARCHAR(100) NOT NULL,
    sent_at             DATETIME     DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asin, group_id)
);

CREATE INDEX idx_sent_at ON products_sent(sent_at);
CREATE INDEX idx_group_id ON products_sent(group_id);
```

---

## 5. Variáveis de Ambiente

### Arquivo `.env.example`

```env
# ─── Amazon PA API 5.0 ───────────────────────────────────
AMAZON_ACCESS_KEY=sua_access_key_aqui
AMAZON_SECRET_KEY=sua_secret_key_aqui
AMAZON_PARTNER_TAG=seu_partner_tag-20
AMAZON_COUNTRY=BR

# ─── OpenAI ──────────────────────────────────────────────
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini

# ─── UAZAPI ──────────────────────────────────────────────
UAZAPI_BASE_URL=http://localhost:3000
UAZAPI_TOKEN=seu_token_uazapi_aqui
WHATSAPP_GROUP_ID=120363xxxxxxxxxx@g.us

# ─── Configurações do Bot ────────────────────────────────
SEND_HOUR=20
MAX_PRODUCTS_PER_SEND=3
MIN_DISCOUNT_PERCENT=20
MIN_RATING=4.0
DAYS_BEFORE_RESEND=30

# ─── Banco de Dados ──────────────────────────────────────
DATABASE_URL=sqlite:///./data/bot.db

# ─── Logging ─────────────────────────────────────────────
LOG_LEVEL=INFO
LOG_FILE=./logs/bot.log
```

---

## 6. Containerização (Docker)

### `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs data

CMD ["python", "main.py"]
```

### `docker-compose.yml`

```yaml
version: "3.9"

services:
  bot:
    build: .
    container_name: amazon_affiliate_bot
    restart: always
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - uazapi
    networks:
      - bot_network

  uazapi:
    image: uazapi/uazapi:latest   # substituir pela imagem oficial UAZAPI
    container_name: uazapi
    restart: always
    ports:
      - "3000:3000"
    volumes:
      - uazapi_data:/app/data
    environment:
      - LICENSE_TOKEN=${UAZAPI_LICENSE_TOKEN}
    networks:
      - bot_network

volumes:
  uazapi_data:

networks:
  bot_network:
    driver: bridge
```

---

## 7. Infraestrutura (VPS)

### Especificações do Servidor

```
Provedor:   Hetzner Cloud
Plano:      CX22
CPU:        2 vCPU (Intel/AMD)
RAM:        4 GB
Disco:      40 GB SSD NVMe
Localização: Falkenstein (Alemanha)
OS:         Ubuntu 24.04 LTS
IP:         Estático (IPv4 dedicado)
```

### Configuração de Firewall (UFW)

```bash
ufw allow ssh          # porta 22
ufw allow 3000/tcp     # UAZAPI — apenas se precisar acesso externo
ufw enable
```

> Recomendação: a porta 3000 (UAZAPI) deve ser acessível **apenas internamente** na rede Docker. Não expor para internet.

---

## 8. Logging e Observabilidade

### Estratégia de Logs

```
Nível   │ Quando usar
────────┼────────────────────────────────────────────────
INFO    │ Job disparado, produtos encontrados, mensagem enviada
WARNING │ Produto sem desconto suficiente, API lenta, retry
ERROR   │ Falha na API Amazon, falha no envio WhatsApp
CRITICAL│ Variável de ambiente faltando, banco inacessível
```

### Formato de Log

```
2026-04-17 08:00:01 [INFO]  job=manha | Iniciando busca de promoções
2026-04-17 08:00:03 [INFO]  job=manha | Encontrados 12 produtos. Novos: 8
2026-04-17 08:00:05 [INFO]  job=manha | Enviando produto ASIN=B09XYZ123 | 39% OFF | R$54,90
2026-04-17 08:00:06 [INFO]  job=manha | WhatsApp ACK: msg_id=ABCD1234
2026-04-17 08:00:36 [INFO]  job=manha | Enviando produto ASIN=B08ABC456 | 25% OFF | R$89,90
2026-04-17 08:00:37 [INFO]  job=manha | WhatsApp ACK: msg_id=EFGH5678
2026-04-17 08:01:07 [INFO]  job=manha | Job concluído. 2 produtos enviados.
```

---

## 9. Segurança

| Prática | Implementação |
|---|---|
| Credenciais nunca no código | Sempre via `.env` + `python-dotenv` |
| `.env` no `.gitignore` | Nunca comitar credenciais |
| Token UAZAPI não exposto | Enviado apenas em header Authorization |
| UAZAPI porta 3000 interna | Não exposta para internet (só Docker network) |
| Limite de gasto OpenAI | Configurar hard limit no painel da OpenAI |
| Logs sem credenciais | Nunca logar access keys ou tokens |
| Retry com backoff | Evitar flooding de APIs externas |

---

## 10. Estimativa de Custo por Execução

| Recurso | Por execução (3 produtos) | Por mês (60 execuções) |
|---|---|---|
| GPT-4o-mini input ~400 tokens | ~$0.00024 | ~$0.015 |
| GPT-4o-mini output ~300 tokens | ~$0.00036 | ~$0.022 |
| Amazon PA API | Gratuito | Gratuito |
| UAZAPI | Fixo (licença) | R$ 47 |
| **Total API** | **~$0.0006** | **~$0.04** |

Custo de IA é praticamente desprezível. O maior custo fixo é a licença UAZAPI.

---

*Última atualização: abril de 2026*

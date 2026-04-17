# 🛍️ AI Bot Amazon — Afiliado Automatizado (Beleza Feminina)

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?logo=openai&logoColor=white)
![Amazon](https://img.shields.io/badge/Amazon-PA%20API%205.0-FF9900?logo=amazon&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp-UAZAPI-25D366?logo=whatsapp&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

> Bot de afiliado Amazon **100% automatizado** com IA. Busca promoções de produtos de beleza feminina, gera copy persuasiva via GPT-4o-mini e envia para um grupo WhatsApp **1× ao dia** — sem intervenção manual.

---

## 📋 Índice

- [Como Funciona](#️-como-funciona)
- [Stack Tecnológica](#-stack-tecnológica)
- [Pré-requisitos](#-pré-requisitos)
- [Quickstart — Deploy em Produção](#-quickstart--deploy-em-produção)
- [Configuração do Ambiente](#️-configuração-do-ambiente)
- [Como Executar Localmente](#️-como-executar-localmente)
- [Estrutura de Pastas](#-estrutura-de-pastas)
- [Roadmap](#️-roadmap)
- [Regras do Agente de IA](#-regras-do-agente-de-ia)
- [Custos Mensais Estimados](#-custos-mensais-estimados)
- [Avisos Importantes](#️-avisos-importantes)
- [Licença](#-licença)

---

## ⚙️ Como Funciona

```
┌──────────────────────────────────────────────────────────┐
│  APScheduler  →  20h BRT (configurável)                    │
│                                                          │
│  Amazon PA API  →  busca Beauty com ≥20% off, ≥4★       │
│       ↓                                                  │
│  SQLite  →  filtra produtos já enviados (30 dias)        │
│       ↓                                                  │
│  GPT-4o-mini  →  gera copy persuasiva (persona "Bella")  │
│       ↓                                                  │
│  UAZAPI  →  envia para grupo WhatsApp (180s entre msgs)  │
└──────────────────────────────────────────────────────────┘
```

A cada execução o bot:

1. Consulta a **Amazon PA API** em busca de produtos de beleza com desconto relevante (≥ 20%, ≥ 4 estrelas, ≥ 50 avaliações)
2. Filtra via **SQLite** os ASINs já enviados nos últimos 30 dias (anti-repetição)
3. Gera um texto promocional personalizado com **GPT-4o-mini** para cada produto (persona "Bella", tom feminino, 6 linhas + 3–5 emojis)
4. Formata a mensagem com preço, desconto em % e link de afiliado
5. Envia uma mensagem por vez no grupo via **UAZAPI**, com 180 segundos de intervalo entre elas

---

## 🧱 Stack Tecnológica

| Camada | Tecnologia | Versão |
|---|---|---|
| Linguagem | Python | 3.12+ |
| Agendamento | APScheduler | 3.x |
| Amazon Products | `python-amazon-paapi` | 5.x |
| Geração de Copy | OpenAI API (GPT-4o-mini) | Latest |
| WhatsApp | UAZAPI (uazapiGO V2, self-hosted) | Latest |
| Banco de Dados | SQLite + SQLAlchemy | 2.x |
| HTTP Client | `httpx` | 0.27+ |
| Config/Env | `python-dotenv` | 1.x |
| Containerização | Docker + Docker Compose | Latest |
| Servidor | Hetzner VPS CX22 (Ubuntu 24.04) | — |

---

## ✅ Pré-requisitos

### Contas e Credenciais

- [ ] **Programa de Afiliados Amazon Brasil**
  - Cadastro: https://associados.amazon.com.br/
  - Você precisará do seu `Partner Tag` (ex: `meusite-20`)
  - ⚠️ A conta PA API pode ser suspensa se não houver vendas nos primeiros 90 dias

- [ ] **Amazon PA API 5.0** _(liberada após aprovação como afiliado)_
  - Gera: `Access Key` e `Secret Key`

- [ ] **OpenAI API Key**
  - Acesse: https://platform.openai.com/api-keys
  - Defina um limite de gasto mensal ($5–10 para começar)

- [ ] **UAZAPI self-hosted**
  - Acesse: https://uazapi.com — adquira o plano self-hosted
  - Você receberá um `admintoken` para criar instâncias via API

- [ ] **Número WhatsApp dedicado ao bot**
  - Use um chip exclusivo (não o seu número pessoal)
  - Preferencialmente **WhatsApp Business** — contas pessoais têm maior risco de ban

- [ ] **VPS Hetzner CX22** _(ou equivalente com ≥ 2 vCPU / 4 GB RAM)_
  - Ubuntu 24.04 LTS com Docker e Docker Compose instalados

---

## 🚀 Quickstart — Deploy em Produção

> Necessário ter Docker e Docker Compose instalados na VPS.

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/ai_bot_amazon.git
cd ai_bot_amazon

# 2. Configure as variáveis de ambiente
cp .env.example .env
nano .env   # preencha TODAS as credenciais antes de continuar

# 3. Suba os containers (bot + UAZAPI)
docker compose up -d

# 4. Configure a instância UAZAPI (ver passos abaixo)
# 5. Acompanhe os logs
docker compose logs -f bot
```

### 4.1 — Criar instância e conectar ao WhatsApp

Com os containers no ar, execute **na VPS** (port 3000 só acessível localmente):

```bash
# Criar instância — copie o "token" da resposta
curl -X POST http://localhost:3000/instance/create \
  -H "admintoken: SEU_ADMINTOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "bot-amazon"}'

# Salve o token retornado em UAZAPI_TOKEN no .env

# Gerar QR Code para parear o número
curl -X POST http://localhost:3000/instance/connect \
  -H "token: SEU_INSTANCE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'

# Verificar status — aguarde aparecer "connected"
curl http://localhost:3000/instance/status \
  -H "token: SEU_INSTANCE_TOKEN"
```

### 4.2 — Obter o ID do grupo WhatsApp

```bash
# Liste os grupos do número conectado
curl http://localhost:3000/group/list \
  -H "token: SEU_INSTANCE_TOKEN"
# → Copie o campo "id" do seu grupo (formato: 120363xxxxxxxxxx@g.us)
# → Salve em WHATSAPP_GROUP_ID no .env
```

### 4.3 — Reiniciar com o .env completo

```bash
docker compose restart bot
docker compose logs -f bot   # confirme "Scheduler iniciado"
```

---

## ⚙️ Configuração do Ambiente

Copie `.env.example` e preencha com suas credenciais:

```bash
cp .env.example .env
```

Referência de todas as variáveis disponíveis:

```env
# ─── Amazon PA API ───────────────────────────────────────
AMAZON_ACCESS_KEY=sua_access_key
AMAZON_SECRET_KEY=sua_secret_key
AMAZON_PARTNER_TAG=meusite-20          # ex: seunome-20
AMAZON_COUNTRY=BR

# ─── OpenAI ──────────────────────────────────────────────
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# ─── UAZAPI (self-hosted Docker) ─────────────────────────
UAZAPI_BASE_URL=http://uazapi:3000     # rede interna Docker
UAZAPI_TOKEN=token_da_instancia        # gerado em /instance/create
UAZAPI_ADMINTOKEN=admintoken_servidor  # credencial de admin do servidor
WHATSAPP_GROUP_ID=120363xxxxxxxxxx@g.us

# ─── Comportamento do Bot ────────────────────────────────
SEND_HOUR=20                           # horário do envio diário (BRT, 0-23)
MAX_PRODUCTS_PER_SEND=3                # máximo de produtos por rodada
MIN_DISCOUNT_PERCENT=20                # desconto mínimo para incluir (%)
MIN_RATING=4.0                         # avaliação mínima em estrelas
DAYS_BEFORE_RESEND=30                  # dias antes de reenviar o mesmo ASIN

# ─── Banco de Dados ──────────────────────────────────────
DATABASE_URL=sqlite:///./data/bot.db

# ─── Logging ─────────────────────────────────────────────
LOG_LEVEL=INFO
LOG_FILE=./logs/bot.log
```

> ⚠️ **Nunca versione o arquivo `.env`** — ele está no `.gitignore` por padrão.

---

## ▶️ Como Executar Localmente

Útil para desenvolvimento e testes antes do deploy na VPS.

```bash
# 1. Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate        # Linux/macOS
# ou: venv\Scripts\activate     # Windows

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure o .env (UAZAPI_BASE_URL pode ser http://localhost:3000)

# 4. Execute
python main.py
```

---

## 📁 Estrutura de Pastas

```
ai_bot_amazon/
├── .env                        # ⚠️ NUNCA versionar — credenciais reais
├── .env.example                # modelo de variáveis (sem valores reais)
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml          # bot + uazapi self-hosted
├── README.md
│
├── main.py                     # entrypoint — inicializa APScheduler
├── config.py                   # carrega e valida variáveis de ambiente
│
├── services/
│   ├── __init__.py
│   ├── amazon.py               # busca produtos via Amazon PA API
│   ├── openai_copy.py          # gera copy persuasiva via GPT-4o-mini
│   └── whatsapp.py             # envia mensagens via UAZAPI
│
├── database/
│   ├── __init__.py
│   ├── models.py               # modelo SQLAlchemy — ProductSent
│   └── repository.py           # funções de acesso ao banco
│
├── utils/
│   ├── __init__.py
│   └── formatter.py            # monta o texto final da mensagem
│
├── prompts/
│   ├── beauty_general.txt      # prompt base — beleza geral
│   ├── makeup.txt              # prompt — maquiagem
│   ├── skincare.txt            # prompt — skincare
│   ├── haircare.txt            # prompt — cabelo
│   └── perfume.txt             # prompt — perfume
│
├── logs/
│   └── .gitkeep
│
└── docs/
    ├── ARCHITECTURE.md         # arquitetura detalhada do sistema
    └── AGENT_RULES.md          # regras de comportamento do agente
```

---

## 🗺️ Roadmap

### ✅ Fase 1 — Infraestrutura
- [x] VPS Hetzner CX22 provisionada (Ubuntu 24.04 + Docker)
- [x] UAZAPI self-hosted containerizado no Docker Compose
- [x] Porta 3000 exposta apenas localmente (anti-exposição pública)

### ✅ Fase 2 — Base do Projeto Python
- [x] Estrutura de pastas e módulos
- [x] `config.py` com validação de variáveis de ambiente
- [x] Banco de dados SQLite + SQLAlchemy (`ProductSent`)
- [x] Repositório com anti-duplicata (30 dias por ASIN + grupo)

### ✅ Fase 3 — Integração Amazon PA API
- [x] Serviço `amazon.py` com busca na categoria Beauty
- [x] Filtros: desconto ≥ 20%, avaliação ≥ 4.0★, reviews ≥ 50
- [x] Ordenação por desconto DESC, depois rating DESC
- [x] Construção de link de afiliado com `Partner Tag`

### ✅ Fase 4 — Geração de Copy com GPT
- [x] Serviço `openai_copy.py` com persona "Bella"
- [x] 5 prompts especializados por subcategoria (geral, maquiagem, skincare, cabelo, perfume)
- [x] Fallback automático se a API OpenAI estiver indisponível

### ✅ Fase 5 — Integração WhatsApp (UAZAPI)
- [x] Header correto: `token: {INSTANCE_TOKEN}` (não Bearer)
- [x] Endpoint correto: `POST /send/text` com campo `number`
- [x] Verificação de conexão via `GET /instance/status`
- [x] Retry automático (2 tentativas, 10s de espera entre elas)

### ✅ Fase 6 — Orquestração e Agendamento
- [x] `main.py` com APScheduler + CronTrigger (`America/Sao_Paulo`)
- [x] Envio diário único (padrão 20h BRT) com horário configurável via `SEND_HOUR`
- [x] Delay de 180s entre produtos na mesma rodada
- [x] Logging estruturado em arquivo rotativo e console

### ✅ Fase 7 — Containerização e Deploy
- [x] `Dockerfile` Python 3.12 slim otimizado
- [x] `docker-compose.yml` com `restart: always` e volumes persistentes
- [x] Variáveis injetadas via `env_file: .env`

### 🔜 Fase 8 — Otimizações Futuras
- [ ] Rastrear cliques com UTM / link encurtador (Bitly, etc.)
- [ ] A/B testing de horários e formatos de copy
- [x] Enviar imagem do produto junto com o texto (`POST /send/media`)
- [ ] Ampliar subcategorias de busca (esportes, casa, etc.)
- [ ] Escalar para múltiplos grupos WhatsApp

---

## 🤖 Regras do Agente de IA

Consulte [docs/AGENT_RULES.md](docs/AGENT_RULES.md) para as regras completas de comportamento do agente: persona "Bella", conteúdo permitido/proibido, prompt de sistema e limites operacionais.

---

## 💰 Custos Mensais Estimados

| Item | Custo estimado |
|---|---|
| Hetzner VPS CX22 | ~R$ 25/mês |
| UAZAPI self-hosted | ~R$ 29/mês |
| OpenAI API (GPT-4o-mini) | ~R$ 5–10/mês |
| **Total** | **~R$ 59–64/mês** |

O programa de afiliados Amazon paga entre **2% e 10%** de comissão por venda dependendo da categoria.  
Com R$ 1.500 em vendas mensais geradas o projeto já se paga — a partir daí, lucro líquido.

---

## ⚠️ Avisos Importantes

- Use um número WhatsApp **exclusivo** para o bot — nunca o seu número pessoal
- **Nunca versione o `.env`** — contém credenciais sensíveis
- A PA API exige vendas nos primeiros 90 dias; divulgue links manualmente no início
- Respeite os intervalos entre mensagens para evitar ban do número no WhatsApp
- O bot não verifica estoque em tempo real — produtos podem aparecer indisponíveis

---

## 📄 Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

*Projeto iniciado em abril de 2026.*

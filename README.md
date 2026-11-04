<div align="center">

# FACOFFEE · Participation Service

**Microsserviço de cotas e adesões da gestão coletiva da copa do departamento**

[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)](https://fastapi.tiangolo.com/)
[![RabbitMQ](https://img.shields.io/badge/eventos-RabbitMQ-ff6600)](https://www.rabbitmq.com/)
[![Keycloak](https://img.shields.io/badge/auth-Keycloak-4d4d4d)](https://www.keycloak.org/)
[![OpenAPI](https://img.shields.io/badge/contrato-OpenAPI%20%2B%20AsyncAPI-6ba539)](api-docs.yaml)

[Arquitetura](#arquitetura) · [API](#api) · [Eventos](#eventos) · [Regras de negócio](#regras-de-negócio) · [Começando](#começando) · [Testes](#testes)

</div>

A copa dos servidores do departamento tem uma máquina de café expresso mantida pelos próprios interessados, e os gastos com insumos são rateados entre os participantes. O **FACOFFEE** automatiza esse rateio como um sistema distribuído de três microsserviços; este repositório implementa o **Participation**, responsável pelo cadastro de cotas e pelas adesões dos participantes.

Gestores criam cotas (valor, periodicidade e itens cobertos), participantes aderem a uma delas, e o serviço anuncia cada mudança por eventos para que o Finance gere as pendências financeiras.

> [!NOTE]
> Trabalho prático acadêmico. A raiz do repositório traz a infraestrutura compartilhada e os contratos da plataforma; o código desta equipe vive exclusivamente em [`participation/`](participation).

## Arquitetura

O domínio foi decomposto em três *bounded contexts* independentes, cada um com o seu próprio banco:

| Subdomínio | Responsabilidade | Porta |
| :--- | :--- | :--- |
| Users | Contas, autenticação e papéis de acesso | 3001 |
| **Participation** | **Cotas e adesões — este repositório** | **3002** |
| Finance | Faturamento, pendências, despesas e comprovantes | 3003 |

Quatro padrões sustentam a implementação:

- **Decomposition by Subdomain** — as fronteiras acima saem do domínio, não da estrutura técnica.
- **Database per Service** — o serviço só conhece `participation_quotas` e `participation_memberships`. Nenhum `JOIN` atravessa a fronteira: ao aderir, os dados relevantes da cota são copiados para dentro da adesão (veja [RN04](#regras-de-negócio)).
- **Asynchronous Messaging** — publica e consome eventos no RabbitMQ pelo exchange de tópicos `facoffee.events`, sem chamadas síncronas a outros serviços.
- **Retry Pattern** — operações de I/O usam retentativa com *backoff* exponencial e *jitter* via `tenacity`. As configurações prontas estão em [`retry.py`](participation/src/infrastructure/messaging/retry.py): 3 tentativas para banco, 5 para mensageria, 4 para rede.

O código segue separação em camadas: `api/` (HTTP e RBAC) → `application/` (casos de uso e regras) → `domain/` (entidades e erros), com `infrastructure/` atendendo persistência e mensageria.

### Resiliência da publicação

Se o RabbitMQ estiver indisponível no momento de publicar, o evento não é perdido nem derruba a requisição: ele é gravado em `outbox_events_fallback.jsonl` (Outbox simplificado) para reenvio posterior.

## API

Todas as rotas ficam sob o prefixo `/api/participation`. Via API Gateway, troque `localhost:3002` por `localhost:8000`.

| Método | Rota | Acesso |
| :--- | :--- | :--- |
| `POST` | `/api/participation/quotas` | `MANAGER` |
| `GET` | `/api/participation/quotas` | aberto |
| `GET` | `/api/participation/quotas/{quotaId}` | aberto |
| `PATCH` | `/api/participation/quotas/{quotaId}` | `MANAGER` |
| `DELETE` | `/api/participation/quotas/{quotaId}` | `MANAGER` |
| `POST` | `/api/participation/participations` | `PARTICIPANT` |
| `GET` | `/api/participation/participations` | aberto |
| `GET` | `/api/participation/participations/{participationId}` | aberto |
| `PATCH` | `/api/participation/participations/{participationId}` | `MANAGER` ou o próprio dono |
| `GET` | `/health` | aberto |

O `DELETE` de cota é remoção lógica: o status vira `INACTIVE` e o registro é preservado. Listagens aceitam paginação (`page`, `size` até 100) e filtros — `active`, `condition` e `items` para cotas; `userId`, `quotaId`, `status` e `cycle` para adesões.

As roles vêm da claim `roles` do JWT emitido pelo Keycloak, enviado em `Authorization: Bearer <token>`.

> [!WARNING]
> A validação da assinatura do JWT ainda não está implementada: o serviço lê as claims com `get_unverified_claims`. Enquanto isso não mudar, a porta `3002` não deve ser exposta fora da rede interna, já que um token forjado com `roles: ["MANAGER"]` passaria pelo RBAC. O item 5.1 do [SAD](participation/docs/sad.md) exige a validação.

### Exemplos

Criar uma cota:

```bash
curl -X POST 'http://localhost:3002/api/participation/quotas' \
  -H 'Authorization: Bearer <TOKEN_JWT>' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Cota de Café Expresso",
    "description": "Rateio mensal das cápsulas",
    "condition": "DAILY",
    "items": "COFFEE",
    "amount": 50.00,
    "active": true
  }'
```

Aderir a uma cota:

```bash
curl -X POST 'http://localhost:3002/api/participation/participations' \
  -H 'Authorization: Bearer <TOKEN_JWT>' \
  -H 'Content-Type: application/json' \
  -d '{
    "userId": "usr_999",
    "quotaId": "quota_12345",
    "startCycle": "2026-06"
  }'
```

## Eventos

Exchange `facoffee.events`, tipo *topic*, durável.

| Direção | Evento | Routing key / fila | Efeito |
| :--- | :--- | :--- | :--- |
| Publica | `QuotaCreated` | `quota.created` | Anuncia a nova cota ao ecossistema |
| Publica | `MembershipCreated` | `membership.created` | Permite ao Finance abrir a pendência do participante |
| Consome | `UserDeactivated` | fila `users.deactivated` | Cancela as adesões ativas do usuário desativado |

O consumidor roda como processo separado da API, com retentativa de conexão (`tenacity`) e `requeue=False` para que uma mensagem com erro não entre em laço infinito.

## Regras de negócio

| | Regra | Comportamento |
| :--- | :--- | :--- |
| RN01 | Valor da cota | `amount` negativo é rejeitado na criação e na atualização |
| RN02 | Adesão única ativa | Um usuário não pode ter duas adesões ativas ao mesmo tempo — a segunda retorna `409` |
| RN03 | Desativação de cota | Cota com adesões ativas não pode ser desativada |
| RN04 | Snapshot da cota | A adesão guarda uma cópia de nome, condição, itens e valor da cota no momento em que foi feita, de modo que mudanças posteriores não alterem o histórico |

Erros de domínio viram respostas com `code` e `message` — `not_found` (404), `conflict` (409), `validation_error` (400) e os códigos específicos `quota_has_active_participations` e `user_already_has_active_participation`.

## Começando

**Requisitos:** Python 3.10+, Docker e Git.

### 1. Infraestrutura compartilhada

API Gateway (Nginx), Keycloak, RabbitMQ e Mailpit sobem pelo Compose na raiz:

```bash
docker compose up -d
```

> [!IMPORTANT]
> O `docker-compose.yml` monta arquivos de configuração de `nginx/`, `rabbitmq/` e `keycloak/` que **não estão versionados neste repositório** — peça-os a quem mantém a infraestrutura da plataforma, senão o `docker compose up` falha ao montar os volumes. O serviço Python roda sem eles; só o gateway e a autenticação ficam indisponíveis.

Depois de subir: RabbitMQ em `localhost:15672`, Keycloak em `localhost:8080` (`facoffee`/`facoffee`) e Mailpit em `localhost:8025`.

### 2. Ambiente do serviço

```bash
cd participation
python3 -m venv venv
```

| Sistema | Comando de ativação |
| :--- | :--- |
| Linux / macOS | `source venv/bin/activate` |
| Windows | `.\venv\Scripts\Activate.ps1` |

```bash
pip install -r requirements.txt
```

### 3. Execução

A porta `3002` é obrigatória: é o que o API Gateway espera como *upstream*.

```bash
uvicorn src.main:app --host 0.0.0.0 --port 3002 --reload
```

As tabelas são criadas automaticamente na subida. Para escutar os eventos, rode o consumidor em outro terminal:

```bash
python -m src.infrastructure.messaging.consumer
```

Com o serviço no ar: Swagger em `http://localhost:3002/docs`, ReDoc em `/redoc` e *healthcheck* em `/health`.

### Configuração

Tudo tem valor padrão para desenvolvimento local; nada é obrigatório.

| Variável | Padrão | Descrição |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///participation.db` | Banco exclusivo do serviço |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | Broker de eventos |
| `RABBITMQ_QUEUE` | `users.deactivated` | Fila consumida pelo worker |
| `RABBITMQ_RETRY_ATTEMPTS` | `5` | Tentativas de conexão do consumidor |

## Estrutura

```
api-docs.yaml                 # Contrato REST de toda a plataforma (OpenAPI)
async-docs.yaml               # Contrato de eventos (AsyncAPI)
docker-compose.yml            # Gateway, Keycloak, RabbitMQ e Mailpit
participation/
├── docs/sad.md               # Documento de Arquitetura de Software
├── requirements.txt
├── pytest.ini
├── src/
│   ├── main.py               # Entrypoint, lifespan e handler global de erros
│   ├── api/                  # Routers, schemas Pydantic e RBAC
│   ├── application/          # Casos de uso e regras de negócio
│   ├── domain/               # Entidades SQLAlchemy e exceções
│   └── infrastructure/
│       ├── database/         # Engine, sessões e repositórios
│       └── messaging/        # Publisher, consumer, listener e retry
└── tests/
    ├── unit/                 # Modelos, serviços, segurança e listener
    └── integration/          # Rotas e repositórios
```

## Testes

```bash
cd participation
python3 -m pytest
```

A suíte usa `pytest` com `httpx`/`TestClient` e SQLite, cobrindo regras de negócio, RBAC, repositórios e o listener de mensageria. Nenhum teste precisa de RabbitMQ no ar.

> [!NOTE]
> Dos 23 testes, 21 passam. Os dois que falham estão em `tests/integration/test_routers.py` e retornam `500` porque o `TestClient` é instanciado fora de um gerenciador de contexto: sem o `lifespan`, as tabelas não são criadas. O `test_join_participation_endpoint_returns_201` ainda espera `201` para uma cota inexistente, o que seria `404` mesmo com o esquema criado.

## Documentação

| Arquivo | Conteúdo |
| :--- | :--- |
| [`participation/docs/sad.md`](participation/docs/sad.md) | Arquitetura, modelo de dados, decisões, regras de negócio e eventos |
| [`api-docs.yaml`](api-docs.yaml) | Contrato REST dos três subdomínios, com as regras de `x-authorization` |
| [`async-docs.yaml`](async-docs.yaml) | Canais e envelopes dos eventos de domínio |

## Equipe

| Nome | GitHub |
| :--- | :--- |
| Pedro Lucas Cremonini | [@rukaaah](https://github.com/rukaaah) |
| Angelo Antônio de Souza | [@angelo-acds](https://github.com/angelo-acds) |
| Gabriel Mattos | [@GabrielMattosA](https://github.com/GabrielMattosA) |
| Cleiton Pinheiro | [@Ton-07](https://github.com/Ton-07) |

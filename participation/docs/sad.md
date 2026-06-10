# Documento de Arquitetura de Software (SAD)

# Microsserviço Participation — FACOFFEE

---

# 1. Visão Geral

## 1.1 Objetivo

O microsserviço Participation é responsável pela gestão de cotas e adesões dos participantes da copa coletiva do FACOFFEE.

O serviço centraliza as regras de elegibilidade, adesão e manutenção das cotas disponíveis, atuando como responsável pelo ciclo de vida das participações dos usuários.

### Responsabilidades

* Criar e manter cotas de participação;
* Ativar e inativar cotas conforme regras de negócio;
* Criar, consultar e encerrar adesões;
* Garantir regras de elegibilidade e integridade das participações;
* Publicar eventos de domínio para integração com outros microsserviços;
* Consumir eventos necessários para manter consistência do ecossistema.

---

## 1.2 Escopo do Serviço

O serviço atua exclusivamente sobre o domínio de cotas e adesões.

### Dentro do escopo

* Gestão de cotas;
* Gestão de adesões;
* Elegibilidade de participação;
* Publicação de eventos relacionados ao domínio.

### Fora do escopo

* Gestão de usuários e autenticação (Users);
* Controle financeiro e cobranças (Finance);
* Emissão ou validação de comprovantes de pagamento.

---

# 2. Responsabilidades Funcionais

## 2.1 Casos de Uso

O microsserviço deve suportar:

* Cadastro de cotas;
* Consulta de cotas;
* Atualização de cotas;
* Ativação e inativação de cotas;
* Criação de adesões;
* Consulta de adesões;
* Encerramento de adesões;
* Consulta utilizando filtros definidos pelo contrato da API.

---

## 2.2 Endpoints Sob Responsabilidade

Todos os endpoints pertencentes ao grupo **Participation** definidos em `api-docs.yaml`.

Exemplos:

| Método | Endpoint                                          |
| ------ | ------------------------------------------------- |
| POST   | `/participation/quotas`                           |
| GET    | `/participation/quotas`                           |
| GET    | `/participation/quotas/{quotaId}`                 |
| PATCH  | `/participation/quotas/{quotaId}`                 |
| DELETE | `/participation/quotas/{quotaId}`                 |
| POST   | `/participation/participations`                   |
| GET    | `/participation/participations`                   |
| GET    | `/participation/participations/{participationId}` |
| PATCH  | `/participation/participations/{participationId}` |

### Referências Obrigatórias

* `api-docs.yaml`
* `async-docs.yaml`

---

# 3. Decisões Arquiteturais

## 3.1 Decomposition by Subdomain

O domínio do FACOFFEE foi dividido em contextos independentes.

O microsserviço Participation implementa exclusivamente o contexto responsável por cotas e adesões.

### Benefícios

* Baixo acoplamento;
* Evolução independente;
* Separação clara de responsabilidades;
* Facilidade de manutenção.

---

## 3.2 Database per Service

O serviço possui banco de dados próprio e isolado.

### Diretrizes

* Não compartilhar banco com outros serviços;
* Não realizar consultas diretas em bancos externos;
* Armazenar apenas identificadores externos quando necessário.

Exemplo:

```text
userId

```

é armazenado apenas como referência de domínio.

---

## 3.3 Asynchronous Messaging

O serviço utiliza RabbitMQ para integração desacoplada com os demais módulos.

### Objetivos

* Propagação de eventos de negócio;
* Comunicação assíncrona;
* Redução de dependências síncronas;
* Escalabilidade.

---

## 3.4 Retry Pattern

Integrações externas utilizam mecanismos de retentativa automática.

### Aplicações

* Consumo de eventos;
* Publicação de eventos;
* Operações críticas de persistência.

### Estratégia

* Backoff exponencial;
* Limite máximo de tentativas;
* Tratamento de falhas transitórias.

---

# 4. Modelo de Dados

## 4.1 Entidade ParticipationQuota

| Campo | Tipo | Descrição |
| --- | --- | --- |
| id | VARCHAR(50) | Identificador da cota |
| name | VARCHAR(255) | Nome da cota |
| description | VARCHAR(500) | Descrição detalhada da cota (Opcional) |
| condition | VARCHAR(50) | DAILY ou SPORADIC |
| items | VARCHAR(50) | ALL, COFFEE ou COOKIES |
| amount | DECIMAL | Valor da contribuição |
| status | VARCHAR(20) | ACTIVE ou INACTIVE |
| createdBy | VARCHAR(50) | Usuário responsável pela criação |
| createdAt | TIMESTAMP | Data de criação |
| updatedAt | TIMESTAMP | Última atualização |

---

## 4.2 Entidade ParticipationMembership

| Campo | Tipo | Descrição |
| --- | --- | --- |
| id | VARCHAR(50) | Identificador da adesão |
| userId | VARCHAR(50) | Usuário participante |
| quotaId | VARCHAR(50) | Cota vinculada |
| status | VARCHAR(20) | ACTIVE ou CANCELLED |
| startCycle | VARCHAR(7) | Competência inicial |
| endCycle | VARCHAR(7) | Competência final (em caso de cancelamento) |
| quotaSnapshot | JSON/TEXT | Cópia da cota no momento da adesão |
| createdAt | TIMESTAMP | Data de criação |
| updatedAt | TIMESTAMP | Última atualização |
| cancelledAt | TIMESTAMP | Data exata do cancelamento |
| cancellationReason | VARCHAR(500) | Motivo do cancelamento para auditoria |
| cancelledBy | VARCHAR(50) | Usuário (ou sistema) que realizou o cancelamento |

---

## 4.3 Histórico e Auditoria

Mudanças relevantes de estado devem ser registradas para rastreabilidade.

Exemplos:

* Ativação de cota;
* Inativação de cota;
* Criação de adesão;
* Cancelamento de adesão.

---

# 5. Segurança e Autorização

## 5.1 Autenticação

Todos os endpoints protegidos devem validar JWT emitido pelo Keycloak.

Claims utilizadas:

```json
{
  "roles": [
    "MANAGER"
  ]
}
```

---

## 5.2 Controle de Acesso

As permissões devem respeitar as regras definidas em `x-authorization` no contrato OpenAPI.

Diretrizes mínimas:

* Operações administrativas restritas a MANAGER;
* Operações do participante limitadas ao próprio escopo;
* Todas as validações realizadas a partir das roles presentes no JWT.

---

# 6. Regras de Negócio

## RN01 — Valor da Cota

O valor da cota deve ser maior ou igual a zero.

**Erro:** HTTP 400 Bad Request

---

## RN02 — Adesão Única Ativa

Um usuário não pode possuir mais de uma adesão ativa simultaneamente.

**Erro:** HTTP 409 Conflict

---

## RN03 — Desativação de Cota

Uma cota não pode ser inativada enquanto possuir adesões ativas.

**Erro:** HTTP 409 Conflict

---

## RN04 — Snapshot da Cota

Ao criar uma adesão, o sistema deve armazenar uma cópia imutável da cota utilizada.

Campos mínimos:

* name
* condition
* items
* amount

---

## RN05 — Integridade de Status

Alterações de estado devem ser auditáveis e rastreáveis.

---

# 7. Eventos e Integração

## 7.1 Eventos Publicados

Conforme definido em `async-docs.yaml`, o serviço deve publicar eventos relacionados a:

* Criação de cotas;
* Atualização de cotas;
* Criação de adesões;
* Cancelamento de adesões.

Todos os eventos devem possuir:

```json
{
  "eventId": "evt_001",
  "occurredAt": "2026-01-01T00:00:00Z",
  "userId": "usr_123"
}

```

---

## 7.2 Eventos Consumidos

O serviço pode consumir eventos necessários para manter a consistência do domínio.

Exemplo:

| Evento | Ação |
| --- | --- |
| UserDeactivated | Cancelar participações ativas do usuário |

---

## 7.3 Idempotência

Todos os consumidores e publicadores devem garantir processamento idempotente utilizando identificadores únicos de evento.

---

# 8. Resiliência

## 8.1 Consumo de Eventos

### Falhas Tratadas

* Indisponibilidade temporária do RabbitMQ;
* Falhas de conexão;
* Falhas transitórias de persistência.

### Estratégia

* Até 5 tentativas;
* Backoff exponencial;
* Reprocessamento seguro por idempotência.

---

# 9. Qualidade e Critérios de Aceite

## 9.1 Testes Obrigatórios

* Testes unitários;
* Testes de integração;
* Testes de autorização;
* Testes de adesão duplicada;
* Testes de cota inativa;
* Testes de valor inválido;
* Testes de publicação de eventos.

---

## 9.2 Critérios de Aceite

* Endpoints aderentes ao `api-docs.yaml`;
* Eventos aderentes ao `async-docs.yaml`;
* Regras de negócio validadas por testes;
* Controle de acesso funcional;
* Documentação atualizada;
* Serviço executável localmente.

---

# 10. Entregáveis

* Código-fonte do microsserviço Participation;
* Suíte de testes automatizados;
* README com instruções de execução;
* Evidências de integração via eventos;
* Documento de Arquitetura de Software (SAD).

# FACOFFEE - Gestão Coletiva da Copa (Microsserviço: Participation)

O **FACOFFEE** é um sistema distribuído projetado para automatizar o gerenciamento coletivo da copa dos servidores do departamento.

A copa possui uma máquina de café expresso mantida pelos próprios interessados, e os gastos com insumos (café, chás, bolachas, materiais de consumo e manutenção) são rateados entre os participantes. O ecossistema permite que gestores cadastrem cotas, participantes realizem adesões e o sistema controle automaticamente a geração de pendências financeiras e a validação de comprovantes de pagamento.

---

## 🏗️ Arquitetura do Sistema

Para garantir escalabilidade, resiliência e independência no desenvolvimento, o FACOFFEE foi desenhado sob uma arquitetura de **Microsserviços**.

### Decisões Arquiteturais da Equipe

Nossa equipe implementou o projeto baseando-se em quatro padrões arquiteturais fundamentais:

* **Decomposition by Subdomain (DDD):** O domínio complexo da aplicação foi dividido em três subdomínios (Bounded Contexts) claros e independentes:
    * **Users:** Governança de contas, autenticação e papéis de acesso.
    * **Participation (Nosso Escopo):** Regras de negócio sobre a criação e manutenção de cotas, além do gerenciamento de adesões de usuários.
    * **Finance:** Faturamento, pendências, despesas e validação de comprovantes.
* **Database per Service:** Para evitar acoplamento rígido (tight coupling), cada microsserviço possui o seu próprio banco de dados isolado. O nosso serviço gerencia exclusivamente as entidades de cotas e participações, não compartilhando tabelas ou realizando consultas diretas (SQL JOINs) com os bancos de usuários ou do financeiro.
* **Asynchronous Messaging (Event-driven):** A comunicação entre os módulos para atualizações de estado é feita de forma assíncrona. O serviço *Participation* integra-se a essa arquitetura atuando como consumidor: ele escuta o evento `UserDeactivated` no RabbitMQ para cancelar automaticamente as adesões ativas de um usuário desativado, eliminando dependências síncronas entre os serviços.
* **Retry Pattern:** Como o sistema é distribuído e depende de rede, operações de I/O críticas—como o consumo de mensagens no RabbitMQ e as atualizações de status no banco de dados isolado—estão protegidas por lógicas de retentativa automática. Isso garante que instabilidades temporárias não quebrem o fluxo do usuário ou causem perda de eventos no ecossistema.

---

## 🛠️ Stack Tecnológica

O microsserviço de **Participation** foi desenvolvido utilizando as seguintes tecnologias:

* **Linguagem:** Python 3.10+
* **Framework Web:** FastAPI (com Uvicorn)
* **Validação de Contratos:** Pydantic (Modelos gerados automaticamente a partir do OpenAPI)
* **ORM (Banco de Dados):** SQLAlchemy + Alembic (Migrações)
* **Mensageria Assíncrona:** aio-pika (RabbitMQ)
* **Segurança:** python-jose (Validação de JWT/Keycloak)
* **Resiliência:** Tenacity (Retry Pattern)

---

## 📂 Organização do Repositório

A raiz deste repositório contém a infraestrutura base da plataforma e os contratos estabelecidos. O código da nossa equipe vive exclusivamente na pasta `/participation`.

```text
facoffee/
├── api-docs.yaml              # Contrato REST (OpenAPI)
├── async-docs.yaml            # Contrato de Mensageria (AsyncAPI)
├── docker-compose.yml         # Infra base (API Gateway, Keycloak, RabbitMQ)
│
└── participation/             # 📍 DIRETÓRIO DA NOSSA EQUIPE
    ├── requirements.txt       # Dependências do Python
    └── src/
        ├── api/               # Roteamento (Routers), Schemas (Pydantic) e Segurança (RBAC)
        ├── application/       # Lógica de Negócio (Services)
        ├── domain/            # Entidades do Banco (Models) e Exceções Customizadas
        └── infrastructure/    # Conexão com DB e Consumidores do RabbitMQ

```

---

## 🚀 Guia de Instalação e Execução Local

Siga os passos abaixo para configurar o ambiente de desenvolvimento na sua máquina.

### 1. Subindo a Infraestrutura Base (Raiz do Projeto)

Antes de rodar o nosso código Python, precisamos garantir que o Banco de Dados, o RabbitMQ, o Keycloak e o Nginx (API Gateway) estejam rodando.

Na raiz do repositório (`facoffee/`), execute:

```bash
docker compose up -d

```

*Aguarde alguns segundos até que todos os containers estejam saudáveis.*

### 2. Configurando o Ambiente Virtual Python (Pasta Participation)

Nosso microsserviço roda de forma isolada. Nunca instale as dependências globalmente.

```bash
# Entre no diretório da equipe
cd participation

# Crie o ambiente virtual (venv)
python3 -m venv venv

# Ative o ambiente virtual
# No Linux/macOS:
source venv/bin/activate
# No Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Instale as dependências do projeto
pip install -r requirements.txt

```

### 3. Rodando a Aplicação

Com o ambiente virtual ativado (`(venv)` visível no terminal), inicie o servidor FastAPI.

**Atenção:** Nosso serviço deve rodar obrigatoriamente na porta `3002` para que o API Gateway (Nginx) consiga redirecionar o tráfego corretamente.

Dentro da pasta `participation/`, execute:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 3002 --reload

```

### 4. Testando o Acesso

Com o servidor rodando, você pode acessar:

* **API Gateway (Porta de Entrada):** `http://localhost:8000/api/participation/quotas`
* **Swagger Automático (Documentação FastAPI):** `http://localhost:3002/docs`

---

## 📝 Notas para Desenvolvedores da Equipe

* **Atualização de Contratos:** Os arquivos em `src/api/schemas.py` são gerados automaticamente a partir do `api-docs.yaml`. Se houver mudanças no contrato do professor, não edite o schema na mão. Use a ferramenta `datamodel-code-generator`.
* **Regras de Negócio:** Nenhuma lógica de negócio deve ser colocada dentro de `src/api/routers.py`. Use a camada de roteamento apenas para chamar funções da camada `src/application/services.py`.
* **Segurança:** Todas as rotas (exceto as de leitura pública, se houver) devem ser protegidas utilizando a dependência `Depends(require_role([...]))` presente em `src/api/security.py`.

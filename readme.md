# Multi-Orquestrador Oráculo

Processo para utilização do Multi-Orquestrador integrado ao backend do Oráculo.

## Pré-requisitos
- **Docker** e **Docker Compose** instalados e rodando.
- O **backend do Oráculo** deve estar rodando a rede externa `oraculo-network` ao ser iniciado, pois os serviços do orquestrador dependem dela para comunicação.

## Passo a Passo para Iniciar

### 1. Configurar Variáveis de Ambiente
Verifique se o arquivo `.env` na raiz do repositório (`oraculo-multi-agent`) está configurado com as chaves de API e URLs necessárias. Estes valores são repassados para os containers no momento em que sobem.

```
LLM_API_KEY= #chave de api da openai
DATABASE_URL= # banco vetorial com os embeddings dos editais
REDIS_URL=redis://redis:6379
ORACLE_API_TOKEN= # token de confirmação para api da edite
EDITE_URL= http://edite_agent:8003 
ORACULO_URL=http://host.docker.internal:8001
```

### 2. Iniciar o Backend do Oráculo
Certifique-se de que o backend principal do Oráculo está rodando. Ele é responsável por subir a rede `oraculo-network`, além das APIs (como a disponível na porta `8001`) que os agentes vão consultar.

### 3. Subir a Infraestrutura Base (Redis)
O orquestrador requer o Redis para gerenciamento do estado dos agentes e filas de mensagens. Inicie-o primeiro a partir da pasta `infra`:

```bash
cd infra
docker-compose up -d
cd ..
```

### 4. Iniciar os Agentes do Multi-Orquestrador
Na raiz do repositório (onde o arquivo `docker-compose.yml` principal se encontra), rode o comando abaixo para realizar o build e subir os serviços `agent` e `edite_agent`:

```bash
docker-compose up --build -d
```

### 5. Attachment ao Backend do Oráculo
Depois de subir o backend do oráculo rodar o seguinte comando de modo a iniciar a conversa com o Multi-Orquestrador

- Para o agente principal (multi-orquestrador):
  ```bash
  docker attach orchestrator_agent
  ```

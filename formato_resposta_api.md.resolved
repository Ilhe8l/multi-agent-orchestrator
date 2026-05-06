# Formato de Resposta da API (`multiagent/main.py`)

A comunicação entre a API (`multiagent/main.py`) e o frontend é assíncrona, usando o padrão de **Job Queue** através do Redis.

Abaixo estão detalhados os formatos de resposta de cada rota da API para o frontend.

---

## 1. Iniciando um Chat (`POST /api/chat`)
Quando o frontend envia uma nova mensagem para o agente, a API não aguarda a resposta final. Ela cria um *job* para processamento em background e retorna imediatamente um identificador (`job_id`).

**Formato da Resposta:**
```json
{
  "job_id": "423f4b6a-8b1a-4c22-92e1-7df82e6a32a1",
  "status": "pending"
}
```

---

## 2. Buscando o Resultado por Polling (`GET /api/result/{job_id}`)
O frontend faz chamadas periódicas para esta rota passando o `job_id` para verificar o status do processamento. O formato de resposta depende do estado atual do *job*:

### A. Enquanto está processando (Pendente)
```json
{
  "status": "pending"
}
```

### B. Quando finaliza com Sucesso
A API extrai os dados gerados pelo LangGraph e os encapsula no formato abaixo:
```json
{
  "status": "done",
  "type": "success",
  "text": "Texto da resposta gerada pelo agente (prioriza `text_response`, com fallback para `final_response`)",
  "final_response": "Resposta bruta do agente (final_response do grafo)",
  "sql": "Query SQL utilizada (se aplicável, vem de `sql_used`)",
  "data": "Dados brutos / grafo retornados do state (vem de `graph` no state)"
}
```

### C. Quando ocorre um Erro
Se houver uma exceção ou falha durante a execução do agente em background:
```json
{
  "status": "error",
  "text": "Mensagem detalhada do erro gerado pela exceção (e)"
}
```

---

## 3. Buscando Histórico do Chat (`GET /api/history/{thread_id}`)
Se o frontend precisar recuperar o histórico de uma conversa anterior usando o `thread_id`, a rota retorna uma lista de mensagens.

**Formato da Resposta:**
```json
[
  {
    "type": "user",
    "text": "Qual foi o faturamento de ontem?"
  },
  {
    "type": "ai",
    "text": "O faturamento de ontem foi de R$ 10.000,00",
    "data": {
      "type": "success",
      "final_response": "O faturamento de ontem foi de R$ 10.000,00",
      "text": "O faturamento de ontem foi de R$ 10.000,00",
      "sql": "SELECT sum(valor) FROM vendas WHERE data = '2023-10-25'",
      "data": { ... }
    }
  }
]
```
*A mensagem do tipo `"ai"` armazena as mesmas informações do resultado bem-sucedido na chave `"data"`.*

---

## 4. Obtendo Resposta via Streaming SSE (`GET /api/stream/{job_id}`)
Caso o frontend use eventos SSE (Server-Sent Events) no lugar de Polling, ele recebe mensagens em stream contendo os blocos do Redis Stream.

**Formato das mensagens no SSE (`data: ...`):**
1. **Evento de Início:**
   ```json
   {"event": "start", "timestamp": "1710000000.123"}
   ```
2. **Evento Pendente:**
   ```json
   {"event": "pending", "payload": "{\"status\": \"pending\"}"}
   ```
3. **Evento Final (Payload vem como string JSON):**
   ```json
   {
     "event": "final",
     "payload": "{\"status\": \"done\", \"type\": \"success\", \"text\": \"...\", \"final_response\": \"...\", \"sql\": \"...\", \"data\": \"...\"}"
   }
   ```
4. **Evento de Erro:**
   ```json
   {
     "event": "error",
     "payload": "{\"status\": \"error\", \"text\": \"Mensagem do erro\"}"
   }
   ```

---

## Resumo das Chaves do Payload de Resposta (Sucesso)

| Chave | Origem do Estado (LangGraph) | Descrição |
|-------|------------------------------|-----------|
| `status` | Fixo como `"done"` | Indica que a requisição finalizou. |
| `type` | Fixo como `"success"` | Indica que não houve quebra de execução. |
| `text` | `text_response` ou `final_response` | O texto primário a ser lido/renderizado pelo usuário. |
| `final_response` | `final_response` | O texto de resposta final gerado pelo nó do agente no Langgraph. |
| `sql` | `sql_used` | A query SQL executada (útil caso o frontend a renderize no modo debug). |
| `data` | `graph` | Dados tabulares (DataFrames convertidos em JSON) ou dados estruturados (gerados pela tools). |

# Modificações Completas — Backend e Frontend

Passo a passo unificado cobrindo `main.py` e o componente React, alinhando fila Redis Streams, SSE, `thread_id` por conversa e isolamento do worker.

---

## Visão geral da arquitetura final

```
Frontend (React)
  │
  ├── POST /api/chat  { user_input, thread_id }
  │         │
  │         ▼
  │   FastAPI (main.py)
  │         │
  │         ├── XADD stream:job:{job_id} "pending"
  │         ├── BackgroundTask → run_graph_job
  │         └── retorna { job_id }
  │
  ├── EventSource /api/stream/{job_id}
  │         │
  │         ▼
  │   XREAD block=0 → aguarda XADD "final" do run_graph_job
  │         │
  │         └── empurra evento SSE ao frontend
  │
  └── Monta aiMessage com dados recebidos
```

---

## PARTE 1 — Backend (`main.py`)

---

### Passo 1 — Restaurar `TTL_CONFIG` no `AsyncRedisSaver`

O `TTL_CONFIG` foi removido em relação à versão anterior. Sem ele, os checkpoints do LangGraph ficam no Redis indefinidamente.

```python
# Antes
async with AsyncRedisSaver.from_conn_string(REDIS_URL) as _checkpointer:

# Depois
TTL_CONFIG = {"default_ttl": 3600, "refresh_on_read": True}

async with AsyncRedisSaver.from_conn_string(REDIS_URL, ttl=TTL_CONFIG) as _checkpointer:
```

> `refresh_on_read: True` renova o TTL toda vez que o checkpointer lê o estado — conversas ativas ficam vivas, conversas abandonadas expiram sozinhas.

---

### Passo 2 — Adicionar grupo de consumidores no Stream

Atualmente o Stream não usa grupos — sem `XACK`, jobs que caem no meio do `ainvoke` somem. Adicione a criação do grupo no `lifespan`:

```python
STREAM_GROUP = "workers"
STREAM_NAME  = "chat:jobs"   # fila central de jobs (opcional, ver Passo 3)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _checkpointer, _graph, _redis_client

    _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

    # Cria grupo de consumidores (ignora se já existir)
    try:
        await _redis_client.xgroup_create(
            STREAM_NAME, STREAM_GROUP, id="0", mkstream=True
        )
    except Exception:
        pass  # grupo já existe

    TTL_CONFIG = {"default_ttl": 3600, "refresh_on_read": True}

    async with AsyncRedisSaver.from_conn_string(REDIS_URL, ttl=TTL_CONFIG) as _checkpointer:
        await _checkpointer.asetup()
        _graph = builder.compile(checkpointer=_checkpointer)
        yield

    await _redis_client.aclose()
```

---

### Passo 3 — Adicionar `XACK` no `run_graph_job`

Após processar com sucesso, confirme a entrega para que o Redis saiba que o job foi concluído:

```python
async def run_graph_job(job_id: str, user_input: str, thread_id: str, msg_id: str = None):
    stream_key = f"stream:job:{job_id}"
    history_key = f"chat:history:{thread_id}"
    config = {"configurable": {"thread_id": thread_id}}

    try:
        await _redis_client.xadd(stream_key, {
            "event": "start",
            "timestamp": str(time.time())
        })

        result = await process_message(user_input, config)

        payload = {
            "status": "done",
            "type": result.get("type"),
            "text": result.get("text") or "Não consegui gerar uma resposta.",
            "final_response": result.get("final_response"),
            "sql": result.get("sql"),
            "data": result.get("data"),
        }

        await _redis_client.xadd(stream_key, {
            "event": "final",
            "payload": json.dumps(payload, default=str)
        })

        # Confirma entrega — job não será reprocessado
        if msg_id:
            await _redis_client.xack(STREAM_NAME, STREAM_GROUP, msg_id)

        await _redis_client.rpush(history_key, json.dumps({"type": "user", "text": user_input}))
        await _redis_client.rpush(history_key, json.dumps({"type": "ai", "text": result.get("text"), "data": result}))
        await _redis_client.expire(stream_key, JOB_TTL)
        await _redis_client.expire(history_key, 86400)

    except Exception as e:
        await _redis_client.xadd(stream_key, {
            "event": "error",
            "payload": json.dumps({"status": "error", "text": str(e)})
        })
        # Não faz XACK em erro — permite reprocessamento manual futuro
```

---

### Passo 4 — Adicionar `thread_id` ao modelo de entrada

O frontend passará `thread_id` gerado por conversa. Garanta que o modelo Pydantic aceita e repassa:

```python
# Antes
class ChatRequest(BaseModel):
    user_input: str
    thread_id: str = "default_session"

# Depois — sem alteração no modelo, mas valide que o endpoint repassa corretamente
@app.post("/api/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid4())
    stream_key = f"stream:job:{job_id}"

    await _redis_client.xadd(stream_key, {
        "event": "pending",
        "payload": json.dumps({"status": "pending"})
    })

    # thread_id agora vem do frontend — não é mais "default_session"
    background_tasks.add_task(
        run_graph_job,
        job_id,
        request.user_input,
        request.thread_id,      # ← repassado diretamente
    )

    return {"job_id": job_id, "status": "pending"}
```

---

### Passo 5 — Adicionar TTL no stream após criação

O stream `stream:job:{job_id}` atualmente só recebe TTL quando o job termina com sucesso. Se o job falhar antes do `xadd "final"`, o stream fica sem TTL. Corrija adicionando TTL no momento da criação:

```python
@app.post("/api/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid4())
    stream_key = f"stream:job:{job_id}"

    await _redis_client.xadd(stream_key, {
        "event": "pending",
        "payload": json.dumps({"status": "pending"})
    })

    # TTL garantido desde a criação — independente do resultado
    await _redis_client.expire(stream_key, JOB_TTL)

    background_tasks.add_task(
        run_graph_job,
        job_id,
        request.user_input,
        request.thread_id,
    )

    return {"job_id": job_id, "status": "pending"}
```

---

### Passo 6 — Adicionar endpoint de histórico com validação

O endpoint `/api/history/{thread_id}` existe mas não valida se o `thread_id` tem histórico. Adicione tratamento:

```python
@app.get("/api/history/{thread_id}")
async def get_history(thread_id: str):
    history_key = f"chat:history:{thread_id}"
    messages = await _redis_client.lrange(history_key, 0, -1)

    if not messages:
        return []   # retorna lista vazia em vez de 404 — frontend não precisa tratar erro

    return [json.loads(m) for m in messages]
```

---

### `main.py` final

```python
import os
import json
import time
import asyncio
import warnings
from uuid import uuid4
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langchain_core.messages import HumanMessage
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis
from graph import builder

warnings.filterwarnings("ignore", category=UserWarning)
load_dotenv()

REDIS_URL    = os.getenv("REDIS_URL", "redis://redis:6379")
JOB_TTL      = 300
TTL_CONFIG   = {"default_ttl": 3600, "refresh_on_read": True}
STREAM_GROUP = "workers"
STREAM_NAME  = "chat:jobs"

_checkpointer = None
_graph        = None
_mcp_tools_loaded = False
_redis_client: aioredis.Redis = None

from mcp_client import get_mcp_client
import router
import graph


async def ensure_mcp_tools():
    global _mcp_tools_loaded
    if _mcp_tools_loaded:
        return
    async with get_mcp_client() as mcp_client:
        tools = await mcp_client.get_tools()
        router.mcp_tools = tools
        graph.mcp_tools  = tools
    _mcp_tools_loaded = True
    print(f"[Startup] MCP tools carregadas: {[t.name for t in router.mcp_tools]}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _checkpointer, _graph, _redis_client

    _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

    try:
        await _redis_client.xgroup_create(
            STREAM_NAME, STREAM_GROUP, id="0", mkstream=True
        )
    except Exception:
        pass

    async with AsyncRedisSaver.from_conn_string(REDIS_URL, ttl=TTL_CONFIG) as _checkpointer:
        await _checkpointer.asetup()
        _graph = builder.compile(checkpointer=_checkpointer)
        yield

    await _redis_client.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    user_input: str
    thread_id: str = "default_session"


async def process_message(user_input: str, config: dict):
    await ensure_mcp_tools()

    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_input": user_input,
        "next_agent": None,
        "delegation_instruction": None,
        "final_response": None,
        "graph": None,
        "sql_used": None,
        "text_response": None,
        "calls": []
    }

    final_state = await _graph.ainvoke(initial_state, config)

    return {
        "type": "success",
        "final_response": final_state.get("final_response"),
        "text": final_state.get("text_response") or final_state.get("final_response"),
        "sql": final_state.get("sql_used"),
        "data": final_state.get("graph"),
    }


async def run_graph_job(job_id: str, user_input: str, thread_id: str, msg_id: str = None):
    stream_key   = f"stream:job:{job_id}"
    history_key  = f"chat:history:{thread_id}"
    config       = {"configurable": {"thread_id": thread_id}}

    try:
        await _redis_client.xadd(stream_key, {
            "event": "start",
            "timestamp": str(time.time())
        })

        result = await process_message(user_input, config)

        payload = {
            "status": "done",
            "type":           result.get("type"),
            "text":           result.get("text") or "Não consegui gerar uma resposta.",
            "final_response": result.get("final_response"),
            "sql":            result.get("sql"),
            "data":           result.get("data"),
        }

        await _redis_client.xadd(stream_key, {
            "event": "final",
            "payload": json.dumps(payload, default=str)
        })

        if msg_id:
            await _redis_client.xack(STREAM_NAME, STREAM_GROUP, msg_id)

        await _redis_client.rpush(history_key, json.dumps({"type": "user", "text": user_input}))
        await _redis_client.rpush(history_key, json.dumps({"type": "ai",   "text": result.get("text"), "data": result}))
        await _redis_client.expire(history_key, 86400)

    except Exception as e:
        await _redis_client.xadd(stream_key, {
            "event": "error",
            "payload": json.dumps({"status": "error", "text": str(e)})
        })


@app.post("/api/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    job_id     = str(uuid4())
    stream_key = f"stream:job:{job_id}"

    await _redis_client.xadd(stream_key, {
        "event": "pending",
        "payload": json.dumps({"status": "pending"})
    })
    await _redis_client.expire(stream_key, JOB_TTL)

    background_tasks.add_task(
        run_graph_job,
        job_id,
        request.user_input,
        request.thread_id,
    )

    return {"job_id": job_id, "status": "pending"}


@app.get("/api/result/{job_id}")
async def get_result(job_id: str):
    stream_key = f"stream:job:{job_id}"
    messages   = await _redis_client.xrevrange(stream_key, count=1)

    if not messages:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    _, data = messages[0]
    event   = data.get("event")

    if event in ("final", "error"):
        return json.loads(data["payload"])

    return {"status": "pending"}


@app.get("/api/stream/{job_id}")
async def stream_job(job_id: str):
    async def event_generator():
        last_id    = "0"
        stream_key = f"stream:job:{job_id}"

        while True:
            results = await _redis_client.xread(
                {stream_key: last_id}, block=0
            )
            for _, messages in results:
                for msg_id, data in messages:
                    last_id = msg_id
                    yield f"data: {json.dumps(data)}\n\n"

                    if data.get("event") in ("final", "error"):
                        return   # fecha o stream após evento terminal

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/history/{thread_id}")
async def get_history(thread_id: str):
    history_key = f"chat:history:{thread_id}"
    messages    = await _redis_client.lrange(history_key, 0, -1)
    return [json.loads(m) for m in messages]


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
```

---

## PARTE 2 — Frontend (React)

---

### Passo 1 — Adicionar `threadId` ao tipo `Conversation`

```typescript
interface Conversation {
  id: string
  threadId: string        // ← novo campo
  title: string
  messages: Message[]
  updatedAt: Date
}
```

---

### Passo 2 — Gerar `threadId` na criação de cada conversa

```typescript
// Onde você cria uma nova conversa:
const newConversation: Conversation = {
  id: Date.now().toString(),
  threadId: crypto.randomUUID(),   // gerado uma vez, nunca muda
  title: "Nova conversa",
  messages: [],
  updatedAt: new Date(),
}
```

---

### Passo 3 — Persistir conversas no localStorage

```typescript
// Inicialização do estado
const loadConversations = (): Conversation[] => {
  try {
    const saved = localStorage.getItem("conversations")
    if (saved) return JSON.parse(saved)
  } catch {}
  return [{
    id: "1",
    threadId: crypto.randomUUID(),
    title: "Nova conversa",
    messages: [],
    updatedAt: new Date(),
  }]
}

const [conversations, setConversations] = useState<Conversation[]>(loadConversations)

// Persiste ao atualizar
useEffect(() => {
  localStorage.setItem("conversations", JSON.stringify(conversations))
}, [conversations])
```

> O `threadId` salvo garante que ao reabrir o browser, o mesmo `thread_id` é enviado ao backend e o `AsyncRedisSaver` recupera o contexto da conversa no Redis.

---

### Passo 4 — Criar helper `waitForJobSSE`

Substitui todo o bloco de polling. Coloque fora do componente:

```typescript
function waitForJobSSE(jobId: string, timeoutMs = 300_000): Promise<any> {
  return new Promise((resolve, reject) => {
    const es = new EventSource(`http://localhost:8004/api/stream/${jobId}`)

    const timer = setTimeout(() => {
      es.close()
      reject(new Error("Timeout: o agente demorou demais para responder."))
    }, timeoutMs)

    es.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.event === "final") {
        clearTimeout(timer)
        es.close()
        resolve(JSON.parse(data.payload))
      }

      if (data.event === "error") {
        clearTimeout(timer)
        es.close()
        reject(new Error(JSON.parse(data.payload).text || "Erro no processamento."))
      }
      // event === "start" | "pending" → aguarda próximo evento
    }

    es.onerror = () => {
      clearTimeout(timer)
      es.close()
      reject(new Error("Conexão SSE perdida."))
    }
  })
}
```

---

### Passo 5 — `handleSend` refatorado

```typescript
const handleSend = useCallback(async () => {
  if (!input.trim() || isLoading) return

  const userMessage = {
    id: Date.now().toString(),
    type: "user",
    text: input,
    timestamp: new Date(),
  }
  const userInput = input
  setInput("")
  setIsLoading(true)

  // Recupera threadId da conversa atual
  const currentConv = conversations.find(c => c.id === currentConvId)
  const threadId = currentConv?.threadId ?? crypto.randomUUID()

  setConversations(prev =>
    prev.map(c => {
      if (c.id !== currentConvId) return c
      return {
        ...c,
        title: c.messages.length === 1 ? userInput.slice(0, 50) : c.title,
        messages: [...c.messages, userMessage],
        updatedAt: new Date(),
      }
    })
  )

  try {
    // ── 1. Enfileira ──
    const postRes = await fetch("http://localhost:8004/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_input: userInput, thread_id: threadId }),
    })
    if (!postRes.ok) throw new Error("Erro ao enfileirar mensagem")
    const { job_id } = await postRes.json()

    // ── 2. Aguarda via SSE ──
    const data = await waitForJobSSE(job_id)

    // ── 3. Monta mensagem ──
    const isScalarResult =
      data.data &&
      data.data.length === 1 &&
      Object.keys(data.data[0]).length === 1

    const aiMessage = {
      id: (Date.now() + 1).toString(),
      type: "ai",
      text: data.type === "fallback"
        ? ""
        : (data.text || data.final_response || "Não consegui processar sua pergunta."),
      final_response: data.final_response,
      timestamp: new Date(),
      sql: data.sql,
      table: data.data,
      isScalarResult,
      chart: !isScalarResult && data.data && data.data.length > 0
        ? data.data.slice(0, 5).map((row: any, i: number) => ({
            name: Object.values(row)[0] || `Item ${i + 1}`,
            value: parseFloat(Object.values(row)[1] as string) || 0,
          }))
        : null,
      isFallback: data.type === "fallback",
      isChat: data.type === "chat",
      fallbackScore: data.score,
      fallbackMessage: data.message,
      suggestions: data.suggestions,
      related_attributes: data.related_attributes,
    }

    setConversations(prev =>
      prev.map(c => {
        if (c.id !== currentConvId) return c
        return { ...c, messages: [...c.messages, aiMessage], updatedAt: new Date() }
      })
    )
  } catch (err: any) {
    const errorMessage = {
      id: (Date.now() + 1).toString(),
      type: "ai",
      text: `Erro ao processar sua pergunta: ${err.message}. Verifique se o backend está rodando.`,
      timestamp: new Date(),
    }
    setConversations(prev =>
      prev.map(c => {
        if (c.id !== currentConvId) return c
        return { ...c, messages: [...c.messages, errorMessage], updatedAt: new Date() }
      })
    )
  } finally {
    setIsLoading(false)
  }
}, [input, isLoading, currentConvId, conversations])
```

---

## Resumo de todas as alterações

### Backend

| # | O que muda | Antes | Depois |
|---|---|---|---|
| 1 | TTL do checkpointer | ausente | `3600s` com `refresh_on_read` |
| 2 | Grupo de consumidores | ausente | `XGROUP CREATE` no lifespan |
| 3 | Confirmação de entrega | ausente | `XACK` após sucesso |
| 4 | TTL do stream | só no final | desde a criação no POST |
| 5 | Stream fecha após evento terminal | loop infinito | `return` após `final` ou `error` |
| 6 | Histórico vazio | erro 500 | retorna `[]` |

### Frontend

| # | O que muda | Antes | Depois |
|---|---|---|---|
| 1 | `thread_id` | `"default_session"` fixo | UUID por conversa |
| 2 | Mecanismo de espera | polling a cada 2s | SSE push imediato |
| 3 | Persistência | ausente | `localStorage` com `threadId` |
| 4 | Tipo `Conversation` | sem `threadId` | com `threadId: string` |
| 5 | Constantes removidas | `POLL_INTERVAL`, `POLL_TIMEOUT` | — |
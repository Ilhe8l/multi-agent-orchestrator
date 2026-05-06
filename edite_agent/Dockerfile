FROM python:3.13-slim

# 1. instala o Poetry
RUN pip install --no-cache-dir poetry

WORKDIR /app

# 2. copia pyproject e lock (caso exista)
COPY pyproject.toml poetry.lock* ./

# 3. configura para não criar virtualenv e instala só as deps principais
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# 4. copia o código da aplicação
COPY . . 

# 5. define o comando de inicialização
CMD ["uvicorn", "apis.oracle_api:app", "--host", "0.0.0.0", "--port", "8003"]

from redis import asyncio as aioredis
import json
import asyncio
from config import REDIS_URL, SYSTEM_PROMPT
import logging

redis_client = None

async def build_prompt() -> str:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    
    editais_data = await redis_client.hgetall("editais_data")
    
    editais = "\n\n".join(
        f"Call ID for use in mentioned_calls: {edital_id}\n"
        f"Name: {json.loads(v)['nome']}\n"
        f"Number: {json.loads(v)['numero']}\n"
        f"Status: {json.loads(v)['status']}\n"
        f"Metadata: {json.dumps(json.loads(v)['metadata'], ensure_ascii=False)}\n"
        f"Tags: {', '.join(json.loads(v)['tags'])}\n"
        f"Sections: {', '.join(json.loads(v)['sections'])}\n"
        #f"Attachments: {', '.join([anexo['nome'] for anexo in json.loads(v)['anexos']])}"
        for edital_id, v in editais_data.items()
    )

    final_prompt = SYSTEM_PROMPT + "\n" + "## The available calls, along with their numbers, sections, attachments, tags, status, and metadata, are:\n" + editais
    return final_prompt

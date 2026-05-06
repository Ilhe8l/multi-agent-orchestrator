from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import logging
from message_gateway import process_message
from config import ORACLE_API_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Oracle API", description="API assíncrona simples para o Oráculo")
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != ORACLE_API_TOKEN:
        logger.warning("Tentativa de acesso com token inválido.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Modelo de entrada, conforme solicitado
class MessageRequest(BaseModel):
    content: str
    session_id: str
    user_id: str

# Modelo de saída
class MessageResponse(BaseModel):
    status: str
    response: str
    session_id: str
    user_id: str

@app.post("/api/message", response_model=MessageResponse)
async def handle_message(request: MessageRequest, token: str = Depends(verify_token)):
    logger.info(f"[START] Mensagem recebida. session_id: {request.session_id}, user_id: {request.user_id}")
    
    try:
        # Chama o process_message e aguarda o resultado
        result = await process_message(
            user_message=request.content, 
            thread_id=request.session_id, 
            user_id=request.user_id
        )

        logger.info(f"[END] Mensagem processada com sucesso.")
        return MessageResponse(
            status="success",
            response=result.get("response", ""),
            session_id=request.session_id,
            user_id=request.user_id
        )
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        # Retorna a mensagem de erro padrão
        return MessageResponse(
            status="error",
            response="*Opa!* Ocorreu um pequeno erro ao processar sua solicitação. Por favor, tente novamente mais tarde.",
            session_id=request.session_id,
            user_id=request.user_id
        )

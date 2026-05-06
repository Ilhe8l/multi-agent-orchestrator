from langchain_core.tools import tool
import psycopg2
from openai import OpenAI
from config import DATABASE_URL, LLM_API_KEY, EMBEDDING_MODEL
from stateTypes import State
import logging

client = None
@tool
def EditalTool(query: str, edital_numbers: list[str] = [], sections: list[str] = [], top_k: int = 3, full_sections: bool = False) -> list[dict]:
    """
    Busca por conteúdo em editais usando embeddings.
    
    Args:
        query: A consulta a ser feita
        edital_numbers: Lista de números de editais. Se vazia, busca em todos os editais
        sections: Lista de seções específicas. Se vazia, busca em todas as seções (use mais de uma seção separando por vírgulas)
        top_k: Número máximo de resultados a retornar
        full_sections: Se True, retorna todas as ocorrências sem limite (ignora top_k, use quando quiser trazer seções inteiras) 
        
    Returns:
        Lista de dicionários com 'edital_number', 'section' e 'content'
    """
    
    logging.info(f"EditalTool chamada com query: {query}, edital_numbers: {edital_numbers}, sections: {sections}, top_k: {top_k}, full_sections: {full_sections}")
    global client
    if client is None:
        try:
            client = OpenAI(api_key=LLM_API_KEY)
        except Exception as e:
            logging.error(f"Erro ao inicializar o cliente OpenAI: {e}")
            return []
    
    try:
        connection = psycopg2.connect(DATABASE_URL)
        cursor = connection.cursor()
        
        # Gerar embedding da query
        embedding = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=query
        ).data[0].embedding
        
        # Construir a query dinamicamente
        conditions = []
        params = []
        
        # Filtro de editais
        if edital_numbers and len(edital_numbers) > 0:
            placeholders = ', '.join(['%s'] * len(edital_numbers))
            conditions.append(f"number IN ({placeholders})")
            params.extend(edital_numbers)
        
        # Filtro de seções
        if sections and len(sections) > 0:
            placeholders = ', '.join(['%s'] * len(sections))
            conditions.append(f"section IN ({placeholders})")
            params.extend(sections)
        
        # Montar WHERE clause
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # Determinar o LIMIT baseado em full_sections E se há seções especificadas 
        use_full_sections = full_sections and sections and len(sections) > 0 # Evita trazer todos os editais completos caso seções não estejam definidas
        limit_clause = "" if use_full_sections else "LIMIT %s"
        
        # Query final
        query_sql = f"""
            SELECT number, section, content
            FROM editais
            {where_clause}
            ORDER BY embedding <-> %s::vector
            {limit_clause}
        """
        
        # Adicionar parâmetros
        params.append(embedding)
        if not full_sections:
            params.append(top_k)
        
        cursor.execute(query_sql, params)
        results = [
            {
                "edital_number": row[0],
                "section": row[1],
                "content": row[2]
            } 
            for row in cursor.fetchall()
        ]
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        logging.error(f"Erro ao executar a consulta no banco de dados: {e}")
        return []
    
    return results
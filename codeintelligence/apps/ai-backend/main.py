from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from context_engine import UnifiedContextEngine
from cloner import RepositoryManager
from postgres_client import PostgresClient
from vector_client import VectorDBClient
from graph_client import GraphDBClient
from models import Repository, FileMetadata
import os

app = FastAPI(title="CodeIntel AI Backend", version="1.0.0")

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

PRODUCTION_FRONTEND_URL = os.getenv("PRODUCTION_FRONTEND_URL")
if PRODUCTION_FRONTEND_URL:
    allowed_origins.append(PRODUCTION_FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,           # Your frontend Dev server URL
    allow_credentials=True,
    allow_methods=["*"],                     # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],                     # Allows all headers
)

# Keep the unified engine warm in memory across API requests
context_engine = UnifiedContextEngine()

# Input Validation Schemas
class IngestRequest(BaseModel):
    repository_url: str
    repository_id: str

class SearchRequest(BaseModel):
    query: str

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "engine": "CodeIntel Gemini Core"}

@app.post("/api/search")
async def semantic_code_search(payload: SearchRequest):
    try:
        # Re-using our standalone agent engine here
        from agent_engine import CodeIntelAgent
        agent = CodeIntelAgent()
        answer = agent.answer_with_context(payload.query)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent runtime error: {str(e)}")

@app.post("/api/ingest")
async def ingest_repository(payload: IngestRequest):
    cloner = RepositoryManager()
    pg_client = PostgresClient()
    v_client = VectorDBClient()
    g_client = GraphDBClient()
    
    repo_path = None
    try:
        # 1. Clone Git assets down to temporary storage
        repo_path = cloner.clone_repo(payload.repository_url, payload.repository_id)
        files = cloner.extract_source_files(repo_path)
        
        # 2. Sync Relational Tables (Neon Postgres)
        session = pg_client.get_session()
        existing_repo = session.query(Repository).filter_by(id=payload.repository_id).first()
        if existing_repo:
            session.delete(existing_repo)
            session.commit()

        new_repo = Repository(id=payload.repository_id, name=payload.repository_id, clone_url=payload.repository_url)
        session.add(new_repo)
        
        # 3. Synchronized Ingestion Data Stream (768-dim Vectors)
        for index, file in enumerate(files):
            db_file = FileMetadata(
                repository_id=payload.repository_id,
                relative_path=file['relative_path'],
                file_extension=file['extension']
            )
            session.add(db_file)
            
            # Requesting 768-dim embeddings from the warm client
            ai_vector = context_engine.search_engine.embedder.get_embedding(file['content'])
            
            vector_metadata = {
                "repository_id": payload.repository_id,
                "file_path": file['relative_path'],
                "content_snippet": file['content'][:500]
            }
            v_client.upsert_code_block(
                point_id=index + 600000, 
                vector=ai_vector, 
                metadata=vector_metadata
            )
            
            # Link dependencies in Neo4j Graph Matrix
            g_client.create_file_node(repo_id=payload.repository_id, file_path=file['relative_path'])

        session.commit()
        session.close()
        
        return {
            "status": "success",
            "repository_id": payload.repository_id,
            "files_indexed": len(files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion engine failure: {str(e)}")
    finally:
        cloner.cleanup(repo_path)
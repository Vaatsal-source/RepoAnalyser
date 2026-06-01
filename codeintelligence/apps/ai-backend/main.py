import sys
import time
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent_engine import CodeIntelAgent, CodeIntelAgenticPlatform
from cloner import RepositoryManager
from context_engine import UnifiedContextEngine
from graph_client import GraphDBClient
from models import FileMetadata, Repository
from postgres_client import PostgresClient
from vector_client import VectorDBClient
import os

app = FastAPI(title="CodeIntel Agentic Backend", version="2.0.0")

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

PRODUCTION_FRONTEND_URL = os.getenv("PRODUCTION_FRONTEND_URL")
if PRODUCTION_FRONTEND_URL:
    allowed_origins.append(PRODUCTION_FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

context_engine = UnifiedContextEngine()
agentic_platform = CodeIntelAgenticPlatform()


class IngestRequest(BaseModel):
    repository_url: str
    repository_id: str


class SearchRequest(BaseModel):
    query: str
    repository_id: str = None


def clean_required_text(value: str, field_name: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail=f"{field_name} is required.")
    return cleaned


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "engine": "CodeIntel LangGraph Multi-Agent Stack"}


@app.post("/api/search/stream")
async def semantic_code_stream(payload: SearchRequest):
    """
    Streams multi-agent reasoning while requiring an explicit workspace scope.
    """
    query = clean_required_text(payload.query, "query")
    repository_id = clean_required_text(payload.repository_id, "repository_id")
    print(f"Received stream query='{query}' workspace='{repository_id}'")

    async def safe_token_generator():
        try:
            generator = agentic_platform.stream_agentic_tokens(
                user_query=query,
                repository_id=repository_id,
            )

            async for token in generator:
                yield token

        except Exception as stream_err:
            print("\nCRITICAL CRASH DETECTED INSIDE AGENTIC GENERATOR:", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print("------------------------------------------------------\n")
            yield f"Backend Agent Engine Exception: {str(stream_err)}"

    return StreamingResponse(safe_token_generator(), media_type="text/event-stream")


@app.post("/api/search")
async def semantic_code_search(payload: SearchRequest):
    """
    Backward compatible non-streaming search route with workspace isolation.
    """
    try:
        query = clean_required_text(payload.query, "query")
        repository_id = clean_required_text(payload.repository_id, "repository_id")
        agent = CodeIntelAgent()
        answer = agent.answer_with_context(
            user_query=query,
            repository_id=repository_id,
        )
        return {"answer": answer}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent runtime error: {str(exc)}")


@app.post("/api/ingest")
async def ingest_repository(payload: IngestRequest):
    cloner = RepositoryManager()
    pg_client = PostgresClient()
    v_client = VectorDBClient()
    g_client = GraphDBClient()

    repo_path = None
    session = None

    try:
        repository_url = clean_required_text(payload.repository_url, "repository_url")
        repository_id = clean_required_text(payload.repository_id, "repository_id")

        v_client.init_collection(vector_size=context_engine.search_engine.embedder.dimension)

        repo_path = cloner.clone_repo(repository_url, repository_id)
        files = cloner.extract_source_files(repo_path)

        session = pg_client.get_session()
        existing_repo = session.query(Repository).filter_by(id=repository_id).first()
        if existing_repo:
            session.delete(existing_repo)
            session.commit()

        v_client.delete_repository_vectors(repository_id)
        try:
            g_client.delete_repository(repository_id)
        except Exception as graph_cleanup_err:
            print(f"Graph cleanup skipped for '{repository_id}': {graph_cleanup_err}")

        new_repo = Repository(
            id=repository_id,
            name=repository_id,
            clone_url=repository_url,
        )
        session.add(new_repo)

        print(f"Processing embeddings for {len(files)} source files...")
        indexed_count = 0
        skipped_files = []

        for index, file in enumerate(files):
            if index > 0:
                time.sleep(5)

            max_retries = 3
            ai_vector = None

            for attempt in range(max_retries):
                try:
                    ai_vector = context_engine.search_engine.embedder.get_embedding(file["content"])
                    break
                except Exception as embed_err:
                    error_msg = str(embed_err)
                    is_quota_error = "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg

                    if is_quota_error and attempt < max_retries - 1:
                        wait_time = 15 * (attempt + 1)
                        print(
                            f"Gemini quota hit on file {index + 1}. "
                            f"Retrying in {wait_time} seconds..."
                        )
                        time.sleep(wait_time)
                        continue

                    if is_quota_error:
                        print(f"Gemini quota exhausted for {file['relative_path']}; skipping.")
                        skipped_files.append(file["relative_path"])
                        break

                    raise embed_err

            if not ai_vector:
                continue

            db_file = FileMetadata(
                repository_id=repository_id,
                relative_path=file["relative_path"],
                file_extension=file["extension"],
            )
            session.add(db_file)

            vector_metadata = {
                "repository_id": repository_id,
                "file_path": file["relative_path"],
                "content_snippet": file["content"][:500],
            }
            v_client.upsert_code_block(
                point_id=v_client.make_point_id(repository_id, file["relative_path"]),
                vector=ai_vector,
                metadata=vector_metadata,
            )

            g_client.create_file_node(repo_id=repository_id, file_path=file["relative_path"])
            indexed_count += 1
            print(f"Indexed {file['relative_path']} ({index + 1}/{len(files)})")

        session.commit()
        return {
            "status": "success",
            "repository_id": repository_id,
            "files_indexed": indexed_count,
            "files_discovered": len(files),
            "files_skipped": skipped_files,
        }

    except HTTPException:
        if session:
            session.rollback()
        raise
    except Exception as exc:
        if session:
            session.rollback()
        print("\nINGESTION CRASH TRACEBACK:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("-----------------------------------\n")
        raise HTTPException(status_code=500, detail=f"Ingestion engine failure: {str(exc)}")
    finally:
        if session:
            session.close()
        cloner.cleanup(repo_path)

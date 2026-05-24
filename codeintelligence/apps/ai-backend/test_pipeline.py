from cloner import RepositoryManager
from postgres_client import PostgresClient
from vector_client import VectorDBClient
from graph_client import GraphDBClient
from embedding_client import GeminiEmbeddingClient
from models import Repository, FileMetadata

def run_gemini_cloud_pipeline():
    print("🚀 Commencing Modern Gemini Cloud Integration Sync Test...")
    
    embedder = GeminiEmbeddingClient()
    pg_client = PostgresClient()
    pg_client.init_tables()
    
    v_client = VectorDBClient()
    # Provision 768 dimensional space on Qdrant for text-embedding-004
    v_client.init_collection(vector_size=768, force_recreate=True)
    
    g_client = GraphDBClient()
    print("🕸️ Established secure handshake with Neo4j Aura Graph Cluster!")

    cloner = RepositoryManager()
    test_url = "https://github.com/octocat/Spoon-Knife" 
    repo_id = "gemini_cloud_sync_test"
    repo_path = None

    try:
        repo_path = cloner.clone_repo(test_url, repo_id)
        files = cloner.extract_source_files(repo_path)
        
        session = pg_client.get_session()
        existing_repo = session.query(Repository).filter_by(id=repo_id).first()
        if existing_repo:
            session.delete(existing_repo)
            session.commit()

        new_repo = Repository(id=repo_id, name="Spoon-Knife", clone_url=test_url)
        session.add(new_repo)
        
        print("\n🧠 Computing Gemini embeddings and streaming to clouds...")
        for index, file in enumerate(files):
            db_file = FileMetadata(
                repository_id=repo_id,
                relative_path=file['relative_path'],
                file_extension=file['extension']
            )
            session.add(db_file)
            
            # Streaming 768-dim cloud coordinates
            ai_vector = embedder.get_embedding(file['content'])
            
            vector_metadata = {
                "repository_id": repo_id,
                "file_path": file['relative_path'],
                "content_snippet": file['content'][:500]
            }
            v_client.upsert_code_block(
                point_id=index + 500000, 
                vector=ai_vector, 
                metadata=vector_metadata
            )
            
            g_client.create_file_node(repo_id=repo_id, file_path=file['relative_path'])
            print(f"   ➔ Gemini Vectorized & Synchronized: {file['relative_path']}")

        session.commit()
        session.close()
        print(f"\n🎉 SUCCESS! Gemini multi-model pipeline processing complete.")

    except Exception as e:
        print(f"❌ Pipeline runtime error: {str(e)}")
    finally:
        cloner.cleanup(repo_path)

if __name__ == "__main__":
    run_gemini_cloud_pipeline()
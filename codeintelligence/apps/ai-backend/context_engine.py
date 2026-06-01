import os
from postgres_client import PostgresClient
from graph_client import GraphDBClient
from search_engine import SemanticSearchEngine
from models import FileMetadata, Repository

class UnifiedContextEngine:
    def __init__(self):
        self.search_engine = SemanticSearchEngine()
        self.pg_client = PostgresClient()
        self.graph_client = GraphDBClient()

    def construct_ai_context(self, user_query: str):
        """
        PRESERVED FOR BACKWARD COMPATIBILITY.
        Executes a monolithic structural-semantic lookup.
        """
        vector_matches = self.search_engine.query_codebase(user_query, limit=1)
        if not vector_matches:
            print("⚠️ No semantic matches found.")
            return None
            
        best_match = vector_matches[0]
        file_path = best_match["file_path"]
        
        print(f"🛠️ Gathering cross-cluster context for: {file_path}")
        
        pg_session = self.pg_client.get_session()
        db_file = pg_session.query(FileMetadata).filter_by(relative_path=file_path).first()
        repo_info = pg_session.query(Repository).filter_by(id=db_file.repository_id).first() if db_file else None
        
        siblings = []
        if db_file:
            try:
                siblings = self.graph_client.get_file_siblings(
                    repo_id=db_file.repository_id, 
                    current_file=file_path
                )
            except Exception as e:
                print(f"⚠️ Graph data pull skipped due to network reset: {e}")

        pg_session.close()

        unified_payload = {
            "query": user_query,
            "target_file": file_path,
            "semantic_similarity_score": best_match["score"],
            "repository": {
                "id": repo_info.id if repo_info else "Unknown",
                "clone_url": repo_info.clone_url if repo_info else "Unknown",
                "indexed_timestamp": str(repo_info.indexed_at) if repo_info else "Unknown"
            },
            "structural_siblings": siblings,
            "raw_content_snippet": best_match["snippet"]
        }
        
        return unified_payload

    # --- AGENTIC TARGETED RETRIEVAL EXTENSIONS ---

    def semantic_code_search(self, query: str, repository_id: str = None, limit: int = 2):
        """
        Executes a targeted semantic query against the vector database layer.
        """
        # FIXED: Forwarding query and repository filtering constraint directly to the active search engine module
        matches = self.search_engine.query_codebase(
            query_text=query, 
            repository_id=repository_id, 
            limit=limit
        )
        return matches

    def relational_meta_lookup(self, file_path: str, repository_id: str = None):
        """Targeted Neon DB transaction tracking data lookup."""
        pg_session = self.pg_client.get_session()
        try:
            print(f"🗄️ [Neon Postgres] Resolving file tracking states for: {file_path}")
            file_query = pg_session.query(FileMetadata).filter_by(relative_path=file_path)
            if repository_id:
                file_query = file_query.filter_by(repository_id=repository_id)

            db_file = file_query.first()
            if db_file:
                repo_info = pg_session.query(Repository).filter_by(id=db_file.repository_id).first()
                return {
                    "file_metadata_id": db_file.id,
                    "repository_id": db_file.repository_id,
                    "repo_url": repo_info.clone_url if repo_info else None
                }
            return None
        except Exception as e:
            print(f"❌ Neon DB processing error: {e}")
            return None
        finally:
            pg_session.close()

    def structural_graph_traverse(self, repo_id: str, current_file: str):
        """Targeted Neo4j Graph traversal engine matching structural dependencies."""
        try:
            print(f"🕸️ [Neo4j Aura] Parsing neighborhood topology structures inside: {repo_id}")
            return self.graph_client.get_file_siblings(repo_id=repo_id, current_file=current_file)
        except Exception as e:
            print(f"❌ Neo4j structural network traversal failed: {e}")
            return []

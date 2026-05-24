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
        # 1. Fetch the primary semantic code asset match from Qdrant
        vector_matches = self.search_engine.query_codebase(user_query, limit=1)
        if not vector_matches:
            print("⚠️ No semantic matches found.")
            return None
            
        best_match = vector_matches[0]
        file_path = best_match["file_path"]
        
        print(f"🛠️ Gathering cross-cluster context for: {file_path}")
        
        # 2. Extract Relational Tracking Meta from Neon Postgres
        pg_session = self.pg_client.get_session()
        db_file = pg_session.query(FileMetadata).filter_by(relative_path=file_path).first()
        repo_info = pg_session.query(Repository).filter_by(id=db_file.repository_id).first() if db_file else None
        
        # 3. Pull structural context from Neo4j Graph using Cypher
        # We find other files bundled in the exact same repository container node
        graph_query = """
        MATCH (r:Repository {id: $repo_id})-[:CONTAINS_FILE]->(sibling:File)
        WHERE sibling.path <> $current_file
        RETURN sibling.path AS sibling_path LIMIT 5
        """
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

        # 4. Compile the complete architecture map
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

if __name__ == "__main__":
    engine = UnifiedContextEngine()
    
    # Run a full composite context retrieval challenge query!
    context_payload = engine.construct_ai_context("Show me the layout structuring scripts.")
    
    print("\n📦 === UNIFIED MULTI-MODEL CONTEXT OBJECT ===")
    import json
    print(json.dumps(context_payload, indent=2))
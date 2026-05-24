from embedding_client import GeminiEmbeddingClient  # <-- Swapped here
from vector_client import VectorDBClient

class SemanticSearchEngine:
    def __init__(self):
        self.embedder = GeminiEmbeddingClient()     # <-- Swapped here
        self.vector_db = VectorDBClient()

    def query_codebase(self, query_text: str, limit=2):
        print(f"\n🔍 Processing natural language query: '{query_text}'")
        
        # Using Gemini model to vectorize the incoming search prompt
        query_vector = self.embedder.get_embedding(query_text)
        
        print("📡 Querying vector similarity space inside Qdrant Cloud...")
        search_results = self.vector_db.client.search(
            collection_name=self.vector_db.collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        
        print(f"🎯 Found {len(search_results)} semantically relevant source documents:\n")
        
        results = []
        for index, hit in enumerate(search_results):
            print(f"🔹 Match #{index + 1} | Score: {hit.score:.4f} (Similarity)")
            print(f"📁 File Path: {hit.payload.get('file_path')}")
            print(f"---")
            
            results.append({
                "score": hit.score,
                "file_path": hit.payload.get("file_path"),
                "snippet": hit.payload.get("content_snippet")
            })
            
        return results

if __name__ == "__main__":
    searcher = SemanticSearchEngine()
    searcher.query_codebase("Where are the main color adjustments and margins defined?", limit=1)
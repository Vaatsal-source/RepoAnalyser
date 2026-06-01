from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from embedding_client import GeminiEmbeddingClient
from vector_client import VectorDBClient


class SemanticSearchEngine:
    def __init__(self):
        self.embedder = GeminiEmbeddingClient()
        self.vector_db = VectorDBClient()

    def query_codebase(self, query_text: str, repository_id: str = None, limit: int = 2):
        """
        Vectorizes a question and runs a repo-scoped similarity lookup in Qdrant.
        """
        query_text = str(query_text or "").strip()
        repository_id = str(repository_id or "").strip()

        print(f"\nProcessing natural language query: '{query_text}'")

        if not repository_id:
            print("No repository_id supplied; refusing global vector search to avoid stale repo leaks.")
            return []

        print(f"Scoping workspace context filter to: '{repository_id}'")
        query_vector = self.embedder.get_embedding(query_text)

        self.vector_db.init_collection(vector_size=self.embedder.dimension)
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="repository_id",
                    match=MatchValue(value=repository_id),
                )
            ]
        )

        print("Querying vector similarity space inside Qdrant Cloud...")
        search_results = self.vector_db.client.search(
            collection_name=self.vector_db.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        print(f"Found {len(search_results)} semantically relevant source documents.\n")

        results = []
        for index, hit in enumerate(search_results):
            print(f"Match #{index + 1} | Score: {hit.score:.4f}")
            print(f"File Path: {hit.payload.get('file_path')}")

            results.append(
                {
                    "score": hit.score,
                    "file_path": hit.payload.get("file_path"),
                    "snippet": hit.payload.get("content_snippet"),
                }
            )

        return results


if __name__ == "__main__":
    searcher = SemanticSearchEngine()
    searcher.query_codebase(
        query_text="Where are the main color adjustments and margins defined?",
        repository_id="example-workspace",
        limit=1,
    )

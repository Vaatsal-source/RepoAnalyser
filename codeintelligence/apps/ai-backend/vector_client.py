import os
import uuid

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL or not QDRANT_API_KEY:
    raise ValueError("QDRANT_URL or QDRANT_API_KEY is missing from your .env file!")


class VectorDBClient:
    def __init__(self):
        self.client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
        )
        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME", "code_segments")

    def _collection_exists(self):
        collections = self.client.get_collections().collections
        return any(c.name == self.collection_name for c in collections)

    def _get_existing_vector_size(self):
        info = self.client.get_collection(collection_name=self.collection_name)
        vectors_config = info.config.params.vectors

        if hasattr(vectors_config, "size"):
            return vectors_config.size

        if isinstance(vectors_config, dict) and vectors_config:
            first_vector = next(iter(vectors_config.values()))
            return getattr(first_vector, "size", None)

        return None

    def ensure_payload_indexes(self):
        """Ensure filtered search by repository_id works for existing collections."""
        info = self.client.get_collection(collection_name=self.collection_name)
        payload_schema = info.payload_schema or {}

        if "repository_id" in payload_schema:
            return

        print("Creating Qdrant payload index on 'repository_id'...")
        try:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="repository_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise

    def init_collection(self, vector_size=768, force_recreate=False):
        """Create or validate the vector collection used by the app."""
        exists = self._collection_exists()

        if exists and force_recreate:
            print(f"Purging old Qdrant collection '{self.collection_name}'...")
            self.client.delete_collection(collection_name=self.collection_name)
            exists = False

        if not exists:
            print(
                f"Creating Qdrant collection '{self.collection_name}' "
                f"with vector size {vector_size}..."
            )
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )
            self.ensure_payload_indexes()
            print("Qdrant collection configured successfully.")
            return

        existing_size = self._get_existing_vector_size()
        if existing_size and existing_size != vector_size:
            raise ValueError(
                f"Qdrant collection '{self.collection_name}' has vector size "
                f"{existing_size}, but the active embedder emits {vector_size}. "
                "Recreate the collection intentionally or set QDRANT_COLLECTION_NAME "
                "to a compatible collection."
            )

        self.ensure_payload_indexes()
        print(f"Qdrant collection '{self.collection_name}' is ready.")

    def make_point_id(self, repository_id, file_path):
        """Build a deterministic UUID so repo/file points never collide."""
        stable_key = f"{str(repository_id).strip()}::{str(file_path).strip()}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, stable_key))

    def delete_repository_vectors(self, repository_id):
        """Remove stale vectors when a workspace id is re-indexed."""
        if not repository_id or not self._collection_exists():
            return

        self.ensure_payload_indexes()
        repo_filter = Filter(
            must=[
                FieldCondition(
                    key="repository_id",
                    match=MatchValue(value=str(repository_id).strip()),
                )
            ]
        )
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=repo_filter,
            wait=True,
        )

    def upsert_code_block(self, point_id, vector, metadata):
        """Push a vector plus repo/file metadata to Qdrant."""
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=metadata,
                )
            ],
        )

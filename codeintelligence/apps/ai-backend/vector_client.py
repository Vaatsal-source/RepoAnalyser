import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL or not QDRANT_API_KEY:
    raise ValueError("❌ QDRANT_URL or QDRANT_API_KEY is missing from your .env file!")

class VectorDBClient:
    def __init__(self):
        # Establish a secure connection to your managed Qdrant Cloud cluster
        self.client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
        )
        self.collection_name = "code_segments"

    def init_collection(self, vector_size=384, force_recreate=False):
        """Creates an isolated vector storage space. Recreates if force_recreate=True."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if exists and force_recreate:
            print(f"🗑️ Dimension shift detected. Purging old 1536-dim collection '{self.collection_name}'...")
            self.client.delete_collection(collection_name=self.collection_name)
            exists = False

        if not exists:
            print(f"📡 Creating fresh collection '{self.collection_name}' on Qdrant Cloud with dim={vector_size}...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size, 
                    distance=Distance.COSINE
                ),
            )
            print("✨ Qdrant collection configured successfully!")
        else:
            print(f"ℹ️ Qdrant collection '{self.collection_name}' already exists.")

    def upsert_code_block(self, point_id, vector, metadata):
        """Pushes a mathematical vector along with its text metadata straight to the cloud."""
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,  # Must be a unique integer or UUID
                    vector=vector,
                    payload=metadata  # Raw source metadata (filepath, content, repo relation)
                )
            ]
        )
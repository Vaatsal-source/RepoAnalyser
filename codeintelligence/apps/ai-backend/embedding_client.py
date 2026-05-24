import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

class GeminiEmbeddingClient:
    def __init__(self):
        print("☁️ Initializing Modern Google GenAI Embedding Client...")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY is missing from your .env file!")
        
        # Canonical SDK instantiation
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-embedding-2" # <-- Updated to the newest production model
        self.dimension = 768               # <-- Target size we want preserved
        print("✅ Gemini Embedding engine online!")

    def get_embedding(self, text: str):
        """Converts raw code snippets into a 768-dimensional vector using modern GenAI."""
        if not text.strip():
            return [0.0] * self.dimension
            
        # Using configuration mapping to enforce 768 dimensions directly from the API
        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config={"output_dimensionality": self.dimension}
        )
        
        return response.embeddings[0].values
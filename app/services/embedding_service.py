from google import genai
from google.genai import types
from app.config import settings

# Embedding output dimensionality — must match the Neo4j vector index (schema.py)
_EMBEDDING_DIM = 768


class EmbeddingService:
    def __init__(self):
        self._client = genai.Client(api_key=settings.google_api_key)
        self._model = settings.gemini_embedding_model

    async def embed_document(self, text: str) -> list[float]:
        """Embed text for storage/indexing (retrieval_document task type)."""
        response = await self._client.aio.models.embed_content(
            model=self._model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=_EMBEDDING_DIM,
            ),
        )
        return list(response.embeddings[0].values)

    async def embed_query(self, text: str) -> list[float]:
        """Embed text for semantic search (retrieval_query task type)."""
        response = await self._client.aio.models.embed_content(
            model=self._model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=_EMBEDDING_DIM,
            ),
        )
        return list(response.embeddings[0].values)


embedding_service = EmbeddingService()

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import settings


class EmbeddingService:
    def __init__(self):
        self._embedder = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.google_api_key,
        )

    async def embed_text(self, text: str) -> list[float]:
        return await self._embedder.aembed_query(text)


embedding_service = EmbeddingService()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    google_api_key: str = ""
    gemini_embedding_model: str = "models/gemini-embedding-001"  # text-embedding-004 unavailable on v1beta

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

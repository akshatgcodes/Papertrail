from pydantic_settings import BaseSettings, SettingsConfigDict

# OpenAI-compatible endpoints, so one client (LangChain's ChatOpenAI) covers all three
PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "ollama": ("http://localhost:11434/v1", "llama3.2"),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/papertrail.db"
    data_dir: str = "./data"
    app_password: str = ""
    session_secret: str = "dev-insecure-secret"
    frontend_url: str = "http://localhost:5173"
    cross_site_cookies: bool = False

    # Generation
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_base_url: str = ""  # defaults to the provider's endpoint
    llm_model: str = ""  # defaults to the provider's model above
    groq_api_key: str = ""  # accepted as an alias for llm_api_key
    llm_max_tokens: int = 8000  # reasoning models spend part of this before answering

    # Embeddings and re-ranking run locally. "hash" / "none" are stand-ins for the tests
    embeddings: str = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker: str = "fastembed"
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"

    # Retrieval: vector search finds candidates, the re-ranker orders them, then at most
    # `per_doc` passages per document go in, so one long document can't crowd out the rest
    candidates: int = 30
    top_k: int = 8
    topic_k: int = 14
    per_doc: int = 3
    # Best passage's cosine similarity below which the library has nothing on the
    # question, and the model isn't called (see docs/DECISIONS.md for the calibration)
    min_similarity: float = 0.68

    # Conflict check: passage pairs from different documents at least this similar are
    # "about the same thing" and get compared; at most `max_conflict_pairs` per question
    conflict_similarity: float = 0.75
    max_conflict_pairs: int = 4

    chunk_chars: int = 1000
    max_upload_mb: int = 20
    max_pages: int = 500
    max_chars: int = 2_000_000  # text extracted from one document
    user_agent: str = "Papertrail/0.1 (personal knowledge base)"

    @property
    def llm(self) -> tuple[str, str, str]:
        """(base_url, model, api_key) with provider defaults filled in."""
        base, model = PROVIDERS.get(self.llm_provider, PROVIDERS["openai"])
        key = (
            self.llm_api_key
            or self.groq_api_key
            or ("ollama" if self.llm_provider == "ollama" else "")
        )
        return self.llm_base_url or base, self.llm_model or model, key


settings = Settings()

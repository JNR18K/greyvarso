import os
from dataclasses import dataclass, field


def _env(name, default=None):
    v = os.getenv(name)
    return v if v not in (None, "") else default


@dataclass
class Config:
    # Cerveau : FreeLLMAPI (endpoint OpenAI-compatible) -> fallback Pollinations (gratuit, sans clé)
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "http://localhost:3001/v1"))
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY", _env("FREELLMAPI_KEY", "")))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "auto"))
    fallback_llm_url: str = field(default_factory=lambda: os.getenv("FALLBACK_LLM_URL", "https://text.pollinations.ai/openai"))
    fallback_llm_model: str = field(default_factory=lambda: _env("FALLBACK_LLM_MODEL", "openai"))
    # Images
    image_url: str = field(default_factory=lambda: _env("IMAGE_URL", "https://image.pollinations.ai/prompt/{prompt}"))
    image_token: str = field(default_factory=lambda: _env("POLLINATIONS_TOKEN", ""))
    image_model: str = field(default_factory=lambda: _env("IMAGE_MODEL", "flux"))
    # Vidéo
    width: int = 1080
    height: int = 1920
    fps: int = 30
    # Certificats (utile derrière un proxy d'entreprise)
    ca_bundle: str = field(default_factory=lambda: _env("SSL_CERT_FILE", _env("REQUESTS_CA_BUNDLE")))
    min_viral_score: int = field(default_factory=lambda: int(_env("MIN_VIRAL_SCORE", "8")))
    max_rewrites: int = field(default_factory=lambda: int(_env("MAX_REWRITES", "2")))

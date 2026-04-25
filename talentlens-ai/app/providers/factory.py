from app.config import Settings
from app.providers.base import LlmProvider
from app.providers.gemini import GeminiProvider
from app.providers.openai import OpenAiProvider


class LlmProviderFactory:
    def __init__(self, settings: Settings):
        self._settings = settings

    def create(self) -> LlmProvider:
        provider = self._settings.llm_provider.strip().lower()
        if provider == "openai":
            return OpenAiProvider(self._settings)
        return GeminiProvider(self._settings)

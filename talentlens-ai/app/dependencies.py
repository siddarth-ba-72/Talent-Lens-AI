from functools import lru_cache

from app.config import Settings, get_settings
from app.providers.base import LlmProvider
from app.providers.factory import LlmProviderFactory
from app.services.jd_parser_service import JdParserService
from app.services.sourcing_workflow_service import SourcingWorkflowService


@lru_cache
def get_llm_provider() -> LlmProvider:
    settings: Settings = get_settings()
    factory = LlmProviderFactory(settings)
    return factory.create()


@lru_cache
def get_jd_parser_service() -> JdParserService:
    provider: LlmProvider = get_llm_provider()
    return JdParserService(provider)


@lru_cache
def get_sourcing_workflow_service() -> SourcingWorkflowService:
    provider: LlmProvider = get_llm_provider()
    settings: Settings = get_settings()
    return SourcingWorkflowService(provider, settings)

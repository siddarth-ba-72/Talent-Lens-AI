from abc import ABC, abstractmethod

from app.models.jd_models import ParsedJdModel


class LlmProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse_jd(self, jd_text: str) -> ParsedJdModel:
        raise NotImplementedError

    @abstractmethod
    def generate_queries(self, parsed_jd: ParsedJdModel, platforms: list[str]) -> dict[str, list[str]]:
        raise NotImplementedError

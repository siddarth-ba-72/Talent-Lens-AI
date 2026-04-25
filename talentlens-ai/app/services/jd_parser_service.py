from fastapi import UploadFile

from app.models.jd_models import ParsedJdModel
from app.providers.base import LlmProvider
from app.services.file_text_extractor import extract_text_from_upload


class JdParserService:
    def __init__(self, provider: LlmProvider):
        self._provider = provider

    def parse_jd_text(self, jd_text: str) -> ParsedJdModel:
        clean_text = jd_text.strip()
        if not clean_text:
            raise ValueError("jdText cannot be blank")
        return self._provider.parse_jd(clean_text)

    async def parse_jd_file(self, file: UploadFile) -> ParsedJdModel:
        text = await extract_text_from_upload(file)
        return self.parse_jd_text(text)

    def generate_queries(self, parsed_jd: ParsedJdModel, platforms: list[str]) -> dict[str, list[str]]:
        return self._provider.generate_queries(parsed_jd, platforms)

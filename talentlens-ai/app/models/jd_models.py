from pydantic import BaseModel, Field


class ParseJdRequest(BaseModel):
    jdText: str = Field(min_length=1)


class ParsedJdModel(BaseModel):
    skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    experienceLevel: str = "Not specified"
    qualifications: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    domain: str = "General"
    summary: str = ""


class GenerateQueriesRequest(BaseModel):
    parsedJd: ParsedJdModel
    platforms: list[str] = Field(default_factory=list)


class GenerateQueriesResponse(BaseModel):
    queriesByPlatform: dict[str, list[str]] = Field(default_factory=dict)

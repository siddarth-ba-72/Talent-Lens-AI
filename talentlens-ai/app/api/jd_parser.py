from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.dependencies import get_jd_parser_service
from app.models.jd_models import GenerateQueriesRequest, GenerateQueriesResponse, ParseJdRequest, ParsedJdModel
from app.services.jd_parser_service import JdParserService


router = APIRouter(prefix="/ai", tags=["jd-parser"])


@router.post("/parse-jd", response_model=ParsedJdModel)
def parse_jd(
    request: ParseJdRequest,
    parser_service: JdParserService = Depends(get_jd_parser_service),
) -> ParsedJdModel:
    try:
        return parser_service.parse_jd_text(request.jdText)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/parse-jd-file", response_model=ParsedJdModel)
async def parse_jd_file(
    jdFile: UploadFile = File(...),
    parser_service: JdParserService = Depends(get_jd_parser_service),
) -> ParsedJdModel:
    try:
        return await parser_service.parse_jd_file(jdFile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate-queries", response_model=GenerateQueriesResponse)
def generate_queries(
    request: GenerateQueriesRequest,
    parser_service: JdParserService = Depends(get_jd_parser_service),
) -> GenerateQueriesResponse:
    queries = parser_service.generate_queries(request.parsedJd, request.platforms)
    return GenerateQueriesResponse(queriesByPlatform=queries)

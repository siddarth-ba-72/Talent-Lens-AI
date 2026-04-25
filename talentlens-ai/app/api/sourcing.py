from fastapi import APIRouter, Depends

from app.dependencies import get_sourcing_workflow_service
from app.models.candidate_models import SourcingRequestPayloadModel, SourcingResultPayloadModel
from app.services.sourcing_workflow_service import SourcingWorkflowService


router = APIRouter(prefix="/ai", tags=["sourcing"])


@router.post("/source-candidates", response_model=SourcingResultPayloadModel)
async def source_candidates(
    payload: SourcingRequestPayloadModel,
    workflow_service: SourcingWorkflowService = Depends(get_sourcing_workflow_service),
) -> SourcingResultPayloadModel:
    return await workflow_service.run(payload)

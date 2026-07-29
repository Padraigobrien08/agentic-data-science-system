"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.artifact_service import ArtifactService
from backend.services.chat_conversation_service import ChatConversationService
from backend.services.edgar_pipeline_execution_service import EdgarPipelineExecutionService
from backend.services.evaluation_control_plane_service import EvaluationControlPlaneService
from backend.services.run_step_service import RunStepService

DbSession = Annotated[Session, Depends(get_db)]


def get_analysis_run_service(db: DbSession) -> AnalysisRunService:
    return AnalysisRunService(db)


def get_chat_conversation_service(db: DbSession) -> ChatConversationService:
    return ChatConversationService(db)


def get_run_step_service(db: DbSession) -> RunStepService:
    return RunStepService(db)


def get_artifact_service(db: DbSession) -> ArtifactService:
    return ArtifactService(db)


def get_edgar_pipeline_execution_service(db: DbSession) -> EdgarPipelineExecutionService:
    return EdgarPipelineExecutionService(db)


def get_evaluation_control_plane_service(db: DbSession) -> EvaluationControlPlaneService:
    return EvaluationControlPlaneService(db)


AnalysisRunServiceDep = Annotated[AnalysisRunService, Depends(get_analysis_run_service)]
ChatConversationServiceDep = Annotated[
    ChatConversationService,
    Depends(get_chat_conversation_service),
]
RunStepServiceDep = Annotated[RunStepService, Depends(get_run_step_service)]
ArtifactServiceDep = Annotated[ArtifactService, Depends(get_artifact_service)]
EdgarPipelineExecutionDep = Annotated[
    EdgarPipelineExecutionService,
    Depends(get_edgar_pipeline_execution_service),
]
EvaluationControlPlaneServiceDep = Annotated[
    EvaluationControlPlaneService,
    Depends(get_evaluation_control_plane_service),
]

__all__ = [
    "AnalysisRunServiceDep",
    "ArtifactServiceDep",
    "ChatConversationServiceDep",
    "DbSession",
    "EdgarPipelineExecutionDep",
    "EvaluationControlPlaneServiceDep",
    "RunStepServiceDep",
    "get_analysis_run_service",
    "get_artifact_service",
    "get_chat_conversation_service",
    "get_db",
    "get_edgar_pipeline_execution_service",
    "get_evaluation_control_plane_service",
    "get_run_step_service",
]

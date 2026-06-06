from collections.abc import Generator
from os import getenv

from fastapi import Body, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
import httpx
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.ai.client import OllamaClient
from app.agent.schemas import AgentControlResponse
from app.agent.service import (
    AgentModeError,
    pause_continuous_agent_mode,
    start_continuous_agent_mode,
    stop_continuous_agent_mode,
)
from app.maintenance.schemas import (
    AuditLogPayload,
    BackupRequest,
    DeletionRequest,
    DeletionResponse,
)
from app.maintenance.service import (
    MaintenanceError,
    MaintenanceEligibilityError,
    create_encrypted_profile_backup,
    delete_profile_data,
    list_audit_logs_for_profile,
    record_audit_log,
)
from app.document_export.service import DocumentExportError, export_resume_version_package
from app.job_analysis.schemas import JobAnalysisResponse
from app.job_analysis.service import (
    JobAnalysisError,
    JobAnalysisValidationError,
    analyze_job_requirements,
)
from app.job_scoring.schemas import JobMatchPayload, ScoreNewJobsResponse
from app.job_scoring.service import JobScoringError, score_job_for_profile, score_new_jobs_for_profile
from app.job_discovery.schemas import JobDiscoveryResult
from app.job_discovery.service import discover_jobs_for_profile
from app.browser_jobs.schemas import BrowserJobPayload, BrowserJobResponse
from app.browser_jobs.service import receive_browser_job
from app.db.session import create_session_factory
from app.resume.parser import ResumeParseError
from app.resume.schemas import (
    MasterResumePayload,
    ResumeEvidencePayload,
    ResumeUploadResponse,
)
from app.resume.service import get_latest_master_resume, ingest_resume_upload, list_resume_evidence
from app.resume.vector_store import NoopResumeVectorStore, QdrantResumeVectorStore
from app.resume_tailoring.schemas import TailoredResumeResponse
from app.resume_tailoring.service import (
    ResumeTailoringEligibilityError,
    ResumeTailoringError,
    tailor_resume_for_profile,
)
from app.ats_validation.schemas import AtsValidationResponse
from app.ats_validation.service import (
    AtsValidationEligibilityError,
    AtsValidationError,
    validate_resume_version_for_profile,
)


class HealthResponse(BaseModel):
    status: str = "ok"


app = FastAPI(title="CareerOS AI API", version="0.1.0")

session_factory = create_session_factory()
vector_store = NoopResumeVectorStore()

if getenv("QDRANT_URL"):
    try:
        from qdrant_client import QdrantClient

        vector_store = QdrantResumeVectorStore(QdrantClient(url=getenv("QDRANT_URL")))
    except Exception:
        vector_store = NoopResumeVectorStore()


def get_db_session() -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_job_discovery_client() -> Generator[httpx.Client, None, None]:
    client = httpx.Client(timeout=30.0)
    try:
        yield client
    finally:
        client.close()


def get_ollama_client() -> Generator[OllamaClient, None, None]:
    client = OllamaClient()
    try:
        yield client
    finally:
        client.close()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/profiles/{profile_id}/resume/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    profile_id: str,
    upload: UploadFile = File(...),
    db: Session = Depends(get_db_session),
) -> ResumeUploadResponse:
    if not upload.filename:
        raise HTTPException(status_code=400, detail="A resume file is required.")

    try:
        file_bytes = await upload.read()
        return ingest_resume_upload(
            db=db,
            profile_id=profile_id,
            file_name=upload.filename,
            mime_type=upload.content_type or "",
            file_bytes=file_bytes,
            vector_store=vector_store,
        )
    except ResumeParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Resume ingestion failed: {exc}") from exc


@app.get("/profiles/{profile_id}/resume/master", response_model=MasterResumePayload)
def get_master_resume(
    profile_id: str, db: Session = Depends(get_db_session)
) -> MasterResumePayload:
    master_resume = get_latest_master_resume(db, profile_id)
    if master_resume is None:
        raise HTTPException(status_code=404, detail="No master resume found for this profile.")
    return MasterResumePayload.model_validate(master_resume, from_attributes=True)


@app.get("/profiles/{profile_id}/resume/evidence", response_model=list[ResumeEvidencePayload])
def get_resume_evidence(
    profile_id: str, db: Session = Depends(get_db_session)
) -> list[ResumeEvidencePayload]:
    evidence = list_resume_evidence(db, profile_id)
    return [ResumeEvidencePayload.model_validate(item, from_attributes=True) for item in evidence]


@app.get("/profiles/{profile_id}/audit-logs", response_model=list[AuditLogPayload])
def get_audit_logs(
    profile_id: str,
    db: Session = Depends(get_db_session),
) -> list[AuditLogPayload]:
    try:
        return [
            AuditLogPayload.model_validate(log, from_attributes=True)
            for log in list_audit_logs_for_profile(db, profile_id)
        ]
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/profiles/{profile_id}/backup", response_class=StreamingResponse)
def export_encrypted_backup(
    profile_id: str,
    payload: BackupRequest,
    db: Session = Depends(get_db_session),
) -> StreamingResponse:
    try:
        file_name, backup_bytes = create_encrypted_profile_backup(
            db=db,
            profile_id=profile_id,
            confirm_profile_name=payload.confirm_profile_name,
            passphrase=payload.passphrase,
        )
        record_audit_log(
            db=db,
            profile_id=profile_id,
            actor_type="user",
            action="export_encrypted_backup",
            entity_type="profile",
            entity_id=profile_id,
            details_json={"file_name": file_name, "backup_bytes": len(backup_bytes)},
        )
        db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MaintenanceEligibilityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MaintenanceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Backup export failed: {exc}") from exc

    return StreamingResponse(
        iter([backup_bytes]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "X-Backup-Encrypted": "true",
        },
    )


@app.delete("/profiles/{profile_id}/data", response_model=DeletionResponse)
def delete_profile_data_route(
    profile_id: str,
    payload: DeletionRequest = Body(...),
    db: Session = Depends(get_db_session),
) -> DeletionResponse:
    try:
        response = delete_profile_data(
            db=db,
            profile_id=profile_id,
            confirm_profile_name=payload.confirm_profile_name,
        )
        record_audit_log(
            db=db,
            profile_id=profile_id,
            actor_type="user",
            action="confirm_profile_data_deletion",
            entity_type="profile",
            entity_id=profile_id,
            details_json=response.model_dump(mode="json"),
        )
        db.commit()
        return response
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MaintenanceEligibilityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MaintenanceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Profile deletion failed: {exc}") from exc


@app.post("/profiles/{profile_id}/agent/discover-jobs", response_model=JobDiscoveryResult)
def discover_jobs(
    profile_id: str,
    db: Session = Depends(get_db_session),
    client: httpx.Client = Depends(get_job_discovery_client),
) -> JobDiscoveryResult:
    try:
        return discover_jobs_for_profile(db=db, profile_id=profile_id, client=client)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Job discovery failed: {exc}") from exc


@app.post("/profiles/{profile_id}/agent/start", response_model=AgentControlResponse)
def start_agent_mode(
    profile_id: str,
    db: Session = Depends(get_db_session),
    client: httpx.Client = Depends(get_job_discovery_client),
) -> AgentControlResponse:
    try:
        return start_continuous_agent_mode(db=db, profile_id=profile_id, client=client)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentModeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Agent start failed: {exc}") from exc


@app.post("/profiles/{profile_id}/agent/pause", response_model=AgentControlResponse)
def pause_agent_mode(
    profile_id: str,
    db: Session = Depends(get_db_session),
) -> AgentControlResponse:
    try:
        return pause_continuous_agent_mode(db=db, profile_id=profile_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentModeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Agent pause failed: {exc}") from exc


@app.post("/profiles/{profile_id}/agent/stop", response_model=AgentControlResponse)
def stop_agent_mode(
    profile_id: str,
    db: Session = Depends(get_db_session),
) -> AgentControlResponse:
    try:
        return stop_continuous_agent_mode(db=db, profile_id=profile_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentModeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Agent stop failed: {exc}") from exc


@app.post("/profiles/{profile_id}/jobs/extracted", response_model=BrowserJobResponse)
def receive_extracted_job(
    profile_id: str,
    payload: BrowserJobPayload,
    db: Session = Depends(get_db_session),
) -> BrowserJobResponse:
    if payload.profile_id != profile_id:
        raise HTTPException(status_code=400, detail="profile_id in path and body must match.")

    try:
        return receive_browser_job(db=db, payload=payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Browser job ingestion failed: {exc}") from exc


@app.post("/profiles/{profile_id}/jobs/{job_id}/score", response_model=JobMatchPayload)
def score_job(
    profile_id: str,
    job_id: str,
    db: Session = Depends(get_db_session),
) -> JobMatchPayload:
    try:
        return score_job_for_profile(db=db, profile_id=profile_id, job_id=job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except JobScoringError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Job scoring failed: {exc}") from exc


@app.post("/profiles/{profile_id}/agent/score-new-jobs", response_model=ScoreNewJobsResponse)
def score_new_jobs(
    profile_id: str,
    db: Session = Depends(get_db_session),
) -> ScoreNewJobsResponse:
    try:
        return score_new_jobs_for_profile(db=db, profile_id=profile_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except JobScoringError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Job scoring failed: {exc}") from exc


@app.post("/profiles/{profile_id}/jobs/{job_id}/tailor-resume", response_model=TailoredResumeResponse)
def tailor_resume(
    profile_id: str,
    job_id: str,
    db: Session = Depends(get_db_session),
) -> TailoredResumeResponse:
    try:
        return tailor_resume_for_profile(db=db, profile_id=profile_id, job_id=job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ResumeTailoringEligibilityError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ResumeTailoringError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Resume tailoring failed: {exc}") from exc


@app.post("/profiles/{profile_id}/resume_versions/{resume_version_id}/validate", response_model=AtsValidationResponse)
def validate_resume_version(
    profile_id: str,
    resume_version_id: str,
    db: Session = Depends(get_db_session),
) -> AtsValidationResponse:
    try:
        return validate_resume_version_for_profile(
            db=db,
            profile_id=profile_id,
            resume_version_id=resume_version_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AtsValidationEligibilityError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AtsValidationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"ATS validation failed: {exc}") from exc


@app.post(
    "/profiles/{profile_id}/resume_versions/{resume_version_id}/export",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "A ZIP archive containing DOCX and PDF exports.",
        }
    },
)
def export_resume_version(
    profile_id: str,
    resume_version_id: str,
    db: Session = Depends(get_db_session),
) -> StreamingResponse:
    try:
        exported = export_resume_version_package(
            db=db,
            profile_id=profile_id,
            resume_version_id=resume_version_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DocumentExportError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Resume export failed: {exc}") from exc

    return StreamingResponse(
        iter([exported.archive_bytes]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{exported.archive_name}"',
            "X-Resume-Version-Id": resume_version_id,
            "X-Docx-File-Name": exported.docx_name,
            "X-Pdf-File-Name": exported.pdf_name,
        },
    )


@app.post("/profiles/{profile_id}/jobs/{job_id}/analyze")
def analyze_job(
    profile_id: str,
    job_id: str,
    db: Session = Depends(get_db_session),
    ai_client: OllamaClient = Depends(get_ollama_client),
) -> JobAnalysisResponse:
    try:
        return analyze_job_requirements(
            db=db,
            profile_id=profile_id,
            job_id=job_id,
            ai_client=ai_client,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except JobAnalysisValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except JobAnalysisError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Job analysis failed: {exc}") from exc

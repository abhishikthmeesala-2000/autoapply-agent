from collections.abc import Generator
from os import getenv

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
import httpx
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.ai.client import OllamaClient
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

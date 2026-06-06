from collections.abc import Generator
from os import getenv

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
import httpx
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.job_discovery.schemas import JobDiscoveryResult
from app.job_discovery.service import discover_jobs_for_profile
from app.db.session import create_session_factory
from app.resume.parser import ResumeParseError
from app.resume.schemas import (
    MasterResumePayload,
    ResumeEvidencePayload,
    ResumeUploadResponse,
)
from app.resume.service import get_latest_master_resume, ingest_resume_upload, list_resume_evidence
from app.resume.vector_store import NoopResumeVectorStore, QdrantResumeVectorStore


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
